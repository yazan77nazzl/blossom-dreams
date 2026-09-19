from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from app.database import get_db
from app.auth import get_current_admin
from app.availability_engine import get_available_slots_for_date
from app.models import AvailabilityConfigResponse, AvailabilityConfigUpdate, DaySchedule, ClosedDateItem
from app.main import limiter

router = APIRouter(prefix="/api/availability", tags=["availability"])

@router.get("/slots")
@limiter.limit("60/minute")
def get_slots(
    request: Request,
    date: str = Query(..., description="YYYY-MM-DD"),
    service_id: Optional[int] = None,
    duration: Optional[int] = None,
    location_id: Optional[int] = None,
):
    duration_to_use = 60
    if service_id:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT duration_minutes FROM services WHERE id = ?", (service_id,))
            row = cursor.fetchone()
            if row:
                duration_to_use = row["duration_minutes"]
    elif duration:
        duration_to_use = duration

    result = get_available_slots_for_date(date, duration_minutes=duration_to_use, service_id=service_id, location_id=location_id)
    return result

@router.get("/config", response_model=AvailabilityConfigResponse)
def get_availability_config(location_id: Optional[int] = None):
    with get_db() as conn:
        cursor = conn.cursor()

        if location_id is not None:
            cursor.execute("SELECT id FROM locations WHERE id = ?", (location_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Location not found.")

            # Effective = global schedule, overridden per-day by the location's own settings.
            cursor.execute("SELECT * FROM location_availability_settings WHERE location_id = ?", (location_id,))
            overrides = {r["day_of_week"]: dict(r) for r in cursor.fetchall()}

            cursor.execute("SELECT * FROM availability_settings ORDER BY day_of_week ASC")
            schedules = []
            for r in cursor.fetchall():
                row = dict(r)
                override = overrides.get(row["day_of_week"])
                if override:
                    row.update(override)
                schedules.append(row)
        else:
            cursor.execute("SELECT * FROM availability_settings ORDER BY day_of_week ASC")
            schedules = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT * FROM closed_dates ORDER BY closed_date ASC")
        closed = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT * FROM locations WHERE is_active = TRUE ORDER BY display_order ASC, id ASC")
        locations = [dict(r) for r in cursor.fetchall()]

    return {
        "schedule": schedules,
        "closed_dates": closed,
        "locations": locations
    }

@router.put("/config")
def update_availability_config(
    update: AvailabilityConfigUpdate,
    location_id: Optional[int] = None,
    current_admin: dict = Depends(get_current_admin),
):
    """Applies the given buffer_minutes to every day of the week (global or for a location)."""
    with get_db() as conn:
        cursor = conn.cursor()

        if location_id is not None:
            cursor.execute("SELECT id FROM locations WHERE id = ?", (location_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Location not found.")

            cursor.execute(
                "SELECT day_of_week, day_name, is_open, open_time, close_time, slot_interval_minutes FROM availability_settings ORDER BY day_of_week ASC"
            )
            for g in cursor.fetchall():
                cursor.execute("""
                INSERT INTO location_availability_settings (
                    location_id, day_of_week, day_name, is_open,
                    open_time, close_time, slot_interval_minutes, buffer_minutes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(location_id, day_of_week) DO UPDATE SET
                    buffer_minutes = excluded.buffer_minutes
                """, (
                    location_id, g["day_of_week"], g["day_name"], g["is_open"],
                    g["open_time"], g["close_time"], g["slot_interval_minutes"],
                    update.buffer_minutes
                ))
            return {"status": "success", "message": f"Buffer updated for location {location_id}"}

        cursor.execute("UPDATE availability_settings SET buffer_minutes = ?", (update.buffer_minutes,))
    return {"status": "success", "message": "Buffer updated"}

@router.put("/schedule/{day_of_week}")
def update_day_schedule(
    day_of_week: int,
    schedule: DaySchedule,
    location_id: Optional[int] = None,
    current_admin: dict = Depends(get_current_admin),
):
    with get_db() as conn:
        cursor = conn.cursor()

        if location_id is not None:
            cursor.execute("SELECT id FROM locations WHERE id = ?", (location_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Location not found.")
            cursor.execute("""
            INSERT INTO location_availability_settings (
                location_id, day_of_week, day_name, is_open,
                open_time, close_time, slot_interval_minutes, buffer_minutes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(location_id, day_of_week) DO UPDATE SET
                day_name = excluded.day_name,
                is_open = excluded.is_open,
                open_time = excluded.open_time,
                close_time = excluded.close_time,
                slot_interval_minutes = excluded.slot_interval_minutes,
                buffer_minutes = excluded.buffer_minutes
            """, (
                location_id, day_of_week, schedule.day_name, schedule.is_open,
                schedule.open_time, schedule.close_time,
                schedule.slot_interval_minutes, schedule.buffer_minutes
            ))
            return {"status": "success", "message": f"Updated schedule for {schedule.day_name} at location {location_id}"}

        cursor.execute("""
        UPDATE availability_settings 
        SET is_open = ?, open_time = ?, close_time = ?, slot_interval_minutes = ?, buffer_minutes = ?
        WHERE day_of_week = ?
        """, (schedule.is_open, schedule.open_time, schedule.close_time, schedule.slot_interval_minutes, schedule.buffer_minutes, day_of_week))
    return {"status": "success", "message": f"Updated schedule for {schedule.day_name}"}

@router.delete("/schedule/{day_of_week}/override")
def delete_day_schedule_override(
    day_of_week: int,
    location_id: int = Query(...),
    current_admin: dict = Depends(get_current_admin),
):
    """Removes a per-location schedule override so the location falls back to the global schedule."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM location_availability_settings WHERE location_id = ? AND day_of_week = ?",
            (location_id, day_of_week)
        )
    return {"status": "success", "message": f"Removed schedule override for day {day_of_week}"}

@router.post("/closed-dates")
def add_closed_date(item: ClosedDateItem, current_admin: dict = Depends(get_current_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM closed_dates WHERE closed_date = ?", (item.closed_date,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Closed date already exists")
        cursor.execute("""
        INSERT INTO closed_dates (closed_date, reason)
        VALUES (?, ?)
        """, (item.closed_date, item.reason))
        new_id = cursor.lastrowid
    return {"status": "success", "id": new_id, "message": "Closed date added"}

@router.delete("/closed-dates/{closed_id}")
def delete_closed_date(closed_id: int, current_admin: dict = Depends(get_current_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM closed_dates WHERE id = ?", (closed_id,))
    return {"status": "success", "message": "Closed date removed"}
