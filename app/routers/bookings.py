import random
import string
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, status
from app.database import get_db
from app.auth import get_current_admin
from app.availability_engine import is_slot_available, time_str_to_minutes, check_intervals_overlap
from app.models import BookingCreate, BookingResponse, BookingStatusUpdate

router = APIRouter(prefix="/api/bookings", tags=["bookings"])

def generate_booking_code() -> str:
    digits = ''.join(random.choices(string.digits, k=5))
    return f"BD-{digits}"

def format_booking_row(row) -> dict:
    d = dict(row)
    return d

@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(booking_in: BookingCreate):
    # 1. Fetch service info
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, price, discount_price, duration_minutes, is_active FROM services WHERE id = ?", (booking_in.service_id,))
        service = cursor.fetchone()
        if not service or not service["is_active"]:
            raise HTTPException(status_code=400, detail="The selected service is not currently available.")

        service_name = service["name"]
        price = service["discount_price"] if service["discount_price"] and service["discount_price"] > 0 else service["price"]
        duration = service["duration_minutes"]

        # 2. Check for slot conflicts atomically
        # Validate that the slot is open in availability settings and no conflicting booking exists
        if not is_slot_available(booking_in.appointment_date, booking_in.appointment_time, duration):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Sorry, this appointment slot is no longer available. Please select another time or date."
            )

        # 3. Double-check direct overlaps within existing non-cancelled bookings
        req_start = time_str_to_minutes(booking_in.appointment_time)
        req_end = req_start + duration

        cursor.execute("""
        SELECT appointment_time, duration_minutes 
        FROM bookings 
        WHERE appointment_date = ? AND status != 'cancelled'
        """, (booking_in.appointment_date,))
        existing = cursor.fetchall()

        for b in existing:
            b_start = time_str_to_minutes(b["appointment_time"])
            b_end = b_start + b["duration_minutes"]
            if check_intervals_overlap(req_start, req_end, b_start, b_end):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This slot was just reserved by another client. Please select a different time."
                )

        # 4. Generate unique booking code
        booking_code = generate_booking_code()
        # Verify code uniqueness
        cursor.execute("SELECT id FROM bookings WHERE booking_code = ?", (booking_code,))
        while cursor.fetchone():
            booking_code = generate_booking_code()
            cursor.execute("SELECT id FROM bookings WHERE booking_code = ?", (booking_code,))

        # 5. Insert booking
        cursor.execute("""
        INSERT INTO bookings (
            booking_code, service_id, customer_name, customer_phone,
            customer_email, notes, appointment_date, appointment_time,
            duration_minutes, status, price
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'confirmed', ?)
        """, (
            booking_code, booking_in.service_id, booking_in.customer_name.strip(),
            booking_in.customer_phone.strip(), booking_in.customer_email.strip() if booking_in.customer_email else None,
            booking_in.notes.strip() if booking_in.notes else None,
            booking_in.appointment_date, booking_in.appointment_time,
            duration, price
        ))
        booking_id = cursor.lastrowid

        cursor.execute("""
        SELECT b.*, s.name as service_name, s.duration_minutes as service_duration
        FROM bookings b
        JOIN services s ON b.service_id = s.id
        WHERE b.id = ?
        """, (booking_id,))
        row = cursor.fetchone()
        return format_booking_row(row)

@router.get("/verify/{code}", response_model=BookingResponse)
def verify_booking(code: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT b.*, s.name as service_name, s.duration_minutes as service_duration
        FROM bookings b
        JOIN services s ON b.service_id = s.id
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
    search: Optional[str] = None,
    current_admin: dict = Depends(get_current_admin)
):
    with get_db() as conn:
        cursor = conn.cursor()
        query = """
        SELECT b.*, s.name as service_name, s.duration_minutes as service_duration
        FROM bookings b
        JOIN services s ON b.service_id = s.id
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
        SELECT b.*, s.name as service_name, s.duration_minutes as service_duration
        FROM bookings b
        JOIN services s ON b.service_id = s.id
        WHERE b.id = ?
        """, (booking_id,))
        return format_booking_row(cursor.fetchone())

@router.delete("/{booking_id}")
def cancel_or_delete_booking(booking_id: int, current_admin: dict = Depends(get_current_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM bookings WHERE id = ?", (booking_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Booking not found")
        cursor.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,))
    return {"status": "success", "message": "Booking marked as cancelled"}

@router.get("/stats/overview")
def get_dashboard_stats(current_admin: dict = Depends(get_current_admin)):
    today_str = date.today().isoformat()
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
        SELECT b.*, s.name as service_name
        FROM bookings b
        JOIN services s ON b.service_id = s.id
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
