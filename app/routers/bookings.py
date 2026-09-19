import random
import string
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, status
from app.database import get_db, IS_POSTGRES
from app.auth import get_current_admin
from app.availability_engine import is_slot_available_for_booking, time_str_to_minutes, local_now
from app.models import BookingCreate, BookingResponse, BookingStatusUpdate

router = APIRouter(prefix="/api/bookings", tags=["bookings"])

def generate_booking_code() -> str:
    digits = ''.join(random.choices(string.digits, k=5))
    return f"BD-{digits}"

def format_booking_row(row) -> dict:
    d = dict(row)
    return d

def _validate_date_time(date_str: str, time_str: str) -> None:
    """Validates the client-supplied date/time format before touching the database."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid appointment date. Expected YYYY-MM-DD.")
    try:
        time_str_to_minutes(time_str)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid appointment time. Expected HH:MM (24h).")

def _acquire_write_lock(conn, cursor, date_str: str) -> None:
    """
    Serializes concurrent booking writes for the same date using PostgreSQL's
    transaction-scoped advisory lock. The lock is held until commit.
    """
    cursor.execute("SELECT pg_advisory_xact_lock(hashtext(?))", (f"blossom_booking:{date_str}",))

@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(booking_in: BookingCreate):
    # 0. Basic customer info sanitation before any DB work
    customer_name = (booking_in.customer_name or "").strip()
    customer_phone = (booking_in.customer_phone or "").strip()
    if len(customer_name) < 2:
        raise HTTPException(status_code=400, detail="Please provide a valid full name.")
    if len(customer_phone) < 5:
        raise HTTPException(status_code=400, detail="Please provide a valid phone number.")

    _validate_date_time(booking_in.appointment_date, booking_in.appointment_time)

    with get_db() as conn:
        cursor = conn.cursor()

        # Serialize concurrent writes for this date — the lock is held until commit.
        _acquire_write_lock(conn, cursor, booking_in.appointment_date)

        # 1. Validate items
        service_ids = booking_in.service_ids or []
        offer_ids = booking_in.offer_ids or []
        if not service_ids and not offer_ids:
            raise HTTPException(status_code=400, detail="Please select at least one service or offer.")

        # Fetch services
        services = []
        total_price = 0.0
        total_duration = 0
        if service_ids:
            placeholders = ','.join(['?'] * len(service_ids))
            cursor.execute(f"SELECT id, name, price, discount_price, duration_minutes, is_active FROM services WHERE id IN ({placeholders})", tuple(service_ids))
            rows = cursor.fetchall()
            if len(rows) != len(service_ids):
                raise HTTPException(status_code=400, detail="One or more selected services not found.")
            for svc in rows:
                if not svc["is_active"]:
                    raise HTTPException(status_code=400, detail=f"Service {svc['name']} is not currently available.")
                svc_price = svc["discount_price"] if svc["discount_price"] and svc["discount_price"] > 0 else svc["price"]
                total_price += svc_price
                total_duration += svc["duration_minutes"]
                services.append(svc)

        # Fetch offers
        offers = []
        if offer_ids:
            placeholders = ','.join(['?'] * len(offer_ids))
            cursor.execute(f"SELECT id, title, discounted_price, duration_minutes, is_active, service_id FROM offers WHERE id IN ({placeholders})", tuple(offer_ids))
            rows = cursor.fetchall()
            if len(rows) != len(offer_ids):
                raise HTTPException(status_code=400, detail="One or more selected offers not found.")
            for off in rows:
                if not off["is_active"]:
                    raise HTTPException(status_code=400, detail=f"Offer {off['title']} is not currently available.")
                total_price += off["discounted_price"]
                total_duration += off.get("duration_minutes", 0) or 0
                offers.append(off)

        # 1b. Validate required location
        location_id = booking_in.location_id
        if location_id is None:
            raise HTTPException(status_code=400, detail="Location is required.")
        cursor.execute("SELECT id, name FROM locations WHERE id = ? AND is_active = TRUE", (location_id,))
        loc_row = cursor.fetchone()
        if not loc_row:
            raise HTTPException(status_code=400, detail="The selected location is not available.")

        # Primary service id for booking row (first selected service or offer's linked service)
        if service_ids:
            primary_service_id = service_ids[0]
        elif offers:
            primary_service_id = offers[0].get("service_id")
            if not primary_service_id:
                raise HTTPException(status_code=400, detail="Selected offer is not linked to a service.")
        else:
            raise HTTPException(status_code=400, detail="No service or offer selected.")

        # 2. Atomically validate the slot against schedule, closed days,
        #    past dates and existing bookings — inside the SAME locked transaction
        #    that performs the insert (prevents the double-booking race).
        available, reason = is_slot_available_for_booking(
            cursor,
            booking_in.appointment_date,
            booking_in.appointment_time,
            total_duration,
            location_id
        )
        if not available:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=reason or "Sorry, this appointment slot is no longer available. Please select another time or date."
            )

        # 3. Duplicate-submission guard: the exact same phone + service + slot
        #    booked within the last few minutes is almost certainly a double
        #    click / retried request, so reject it instead of double-booking.
        duplicate_sql = """
        SELECT id FROM bookings
        WHERE customer_phone = ? AND service_id = ? AND appointment_date = ? AND appointment_time = ?
          AND COALESCE(location_id, -1) = COALESCE(?, -1)
          AND status != 'cancelled'
          AND created_at >= {recent_window}
        LIMIT 1
        """
        recent_window = "NOW() - INTERVAL '5 minutes'"
        cursor.execute(
            duplicate_sql.format(recent_window=recent_window),
            (
                customer_phone,
                primary_service_id,
                booking_in.appointment_date,
                booking_in.appointment_time,
                location_id,
            )
        )
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This appointment was already submitted. Please check your booking code for confirmation."
            )

        # 4. Generate a unique booking code
        booking_code = generate_booking_code()
        # Verify code uniqueness
        cursor.execute("SELECT id FROM bookings WHERE booking_code = ?", (booking_code,))
        while cursor.fetchone():
            booking_code = generate_booking_code()
            cursor.execute("SELECT id FROM bookings WHERE booking_code = ?", (booking_code,))

        # 5. Insert booking with aggregated totals
        cursor.execute("""
        INSERT INTO bookings (
            booking_code, service_id, location_id, customer_name, customer_phone,
            customer_email, notes, appointment_date, appointment_time,
            duration_minutes, status, price
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'confirmed', ?)
        """, (
            booking_code, primary_service_id, location_id, customer_name,
            customer_phone, booking_in.customer_email.strip() if booking_in.customer_email else None,
            booking_in.notes.strip() if booking_in.notes else None,
            booking_in.appointment_date, booking_in.appointment_time,
            total_duration, total_price
        ))
        booking_id = cursor.lastrowid

        # 5b. Insert booking_items for each selected service
        for svc in services:
            svc_price = svc["discount_price"] if svc["discount_price"] and svc["discount_price"] > 0 else svc["price"]
            cursor.execute("""
                INSERT INTO booking_items (booking_id, item_type, item_id, price, duration_minutes)
                VALUES (?, 'service', ?, ?, ?)
            """, (booking_id, svc["id"], svc_price, svc["duration_minutes"]))

        # 5c. Insert booking_items for each selected offer
        for off in offers:
            off_duration = off.get("duration_minutes", 0) or 0
            cursor.execute("""
                INSERT INTO booking_items (booking_id, item_type, item_id, price, duration_minutes)
                VALUES (?, 'offer', ?, ?, ?)
            """, (booking_id, off["id"], off["discounted_price"], off_duration))

        cursor.execute("""
        SELECT b.*, s.name as service_name, s.duration_minutes as service_duration, l.name as location_name
        FROM bookings b
        JOIN services s ON b.service_id = s.id
        LEFT JOIN locations l ON b.location_id = l.id
        WHERE b.id = ?
        """, (booking_id,))
        row = cursor.fetchone()
        return format_booking_row(row)

@router.get("/verify/{code}", response_model=BookingResponse)
def verify_booking(code: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT b.*, s.name as service_name, s.duration_minutes as service_duration, l.name as location_name
        FROM bookings b
        JOIN services s ON b.service_id = s.id
        LEFT JOIN locations l ON b.location_id = l.id
        WHERE b.booking_code = ?
        """, (code.strip().upper(),))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Booking code not found.")
        return format_booking_row(row)

@router.get("", response_model=List[BookingResponse])
def get_bookings(
    date: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    status: Optional[str] = None,
    service_id: Optional[int] = None,
    location_id: Optional[int] = None,
    search: Optional[str] = None,
    current_admin: dict = Depends(get_current_admin)
):
    with get_db() as conn:
        cursor = conn.cursor()
        query = """
        SELECT b.*, s.name as service_name, s.duration_minutes as service_duration, l.name as location_name
        FROM bookings b
        JOIN services s ON b.service_id = s.id
        LEFT JOIN locations l ON b.location_id = l.id
        WHERE 1=1
        """
        params = []

        if date:
            query += " AND b.appointment_date = ?"
            params.append(date)

        if from_date:
            query += " AND b.appointment_date >= ?"
            params.append(from_date)

        if to_date:
            query += " AND b.appointment_date <= ?"
            params.append(to_date)

        if status:
            query += " AND b.status = ?"
            params.append(status)

        if service_id:
            query += " AND b.service_id = ?"
            params.append(service_id)

        if location_id:
            query += " AND b.location_id = ?"
            params.append(location_id)

        if search:
            query += " AND (b.customer_name LIKE ? OR b.customer_phone LIKE ? OR b.booking_code LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term, term])

        query += " ORDER BY b.appointment_date DESC, b.appointment_time ASC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [format_booking_row(r) for r in rows]

@router.patch("/{booking_id}/status", response_model=BookingResponse)
def update_booking_status(
    booking_id: int, 
    status_update: BookingStatusUpdate, 
    current_admin: dict = Depends(get_current_admin)
):
    valid_statuses = ["pending", "confirmed", "completed", "cancelled", "no_show"]
    if status_update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Choose from: {', '.join(valid_statuses)}")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM bookings WHERE id = ?", (booking_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Booking not found")

        cursor.execute("UPDATE bookings SET status = ? WHERE id = ?", (status_update.status, booking_id))

        cursor.execute("""
        SELECT b.*, s.name as service_name, s.duration_minutes as service_duration, l.name as location_name
        FROM bookings b
        JOIN services s ON b.service_id = s.id
        LEFT JOIN locations l ON b.location_id = l.id
        WHERE b.id = ?
        """, (booking_id,))
        return format_booking_row(cursor.fetchone())

@router.delete("/{booking_id}")
def delete_booking(booking_id: int, current_admin: dict = Depends(get_current_admin)):
    """
    Permanently removes a single booking from the database (admin action).
    Verifies the booking exists, then deletes ONLY that booking row. Customers,
    services, locations and all other bookings are untouched, and the freed
    appointment slot immediately becomes available again (slots are computed
    live from the bookings table — nothing is cached).
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM bookings WHERE id = ?", (booking_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Booking not found")
        cursor.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    return {"status": "success", "message": "Booking permanently deleted"}

@router.get("/stats/overview")
def get_dashboard_stats(current_admin: dict = Depends(get_current_admin)):
    today_str = local_now().date().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()

        # Today's appointments
        cursor.execute("SELECT COUNT(*) as count FROM bookings WHERE appointment_date = ? AND status != 'cancelled'", (today_str,))
        today_count = cursor.fetchone()["count"]

        # Upcoming appointments
        cursor.execute("SELECT COUNT(*) as count FROM bookings WHERE appointment_date >= ? AND status != 'cancelled'", (today_str,))
        upcoming_count = cursor.fetchone()["count"]

        # Pending bookings
        cursor.execute("SELECT COUNT(*) as count FROM bookings WHERE status = 'pending'")
        pending_count = cursor.fetchone()["count"]

        # Total services
        cursor.execute("SELECT COUNT(*) as count FROM services WHERE is_active = TRUE")
        services_count = cursor.fetchone()["count"]

        # Active offers
        cursor.execute("SELECT COUNT(*) as count FROM offers WHERE is_active = TRUE AND end_date >= ?", (today_str,))
        active_offers_count = cursor.fetchone()["count"]

        # Total completed bookings & estimated revenue
        cursor.execute("SELECT COUNT(*) as count, COALESCE(SUM(price), 0) as revenue FROM bookings WHERE status IN ('completed', 'confirmed')")
        rev_row = cursor.fetchone()
        total_rev = rev_row["revenue"]
        confirmed_count = rev_row["count"]

        # Today's list preview
        cursor.execute("""
        SELECT b.*, s.name as service_name, l.name as location_name
        FROM bookings b
        JOIN services s ON b.service_id = s.id
        LEFT JOIN locations l ON b.location_id = l.id
        WHERE b.appointment_date = ? AND b.status != 'cancelled'
        ORDER BY b.appointment_time ASC
        LIMIT 10
        """, (today_str,))
        today_appointments = [format_booking_row(r) for r in cursor.fetchall()]

    return {
        "today_appointments_count": today_count,
        "upcoming_appointments_count": upcoming_count,
        "pending_bookings_count": pending_count,
        "total_active_services": services_count,
        "active_offers_count": active_offers_count,
        "confirmed_count": confirmed_count,
        "estimated_revenue": total_rev,
        "today_appointments": today_appointments
    }
