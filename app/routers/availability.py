from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from app.database import get_db
from app.auth import get_current_admin
from app.availability_engine import get_available_slots_for_date
from app.models import AvailabilityConfigResponse, DaySchedule, BreakTimeItem, ClosedDateItem

router = APIRouter(prefix="/api/availability", tags=["availability"])

@router.get("/slots")
def get_slots(date: str = Query(..., description="YYYY-MM-DD"), service_id: Optional[int] = None, duration: Optional[int] = None):
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

    result = get_available_slots_for_date(date, duration_minutes=duration_to_use, service_id=service_id)
    return result

@router.get("/config", response_model=AvailabilityConfigResponse)
def get_availability_config():
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM availability_settings ORDER BY day_of_week ASC")
        schedules = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT * FROM break_times ORDER BY day_of_week ASC, start_time ASC")
        breaks = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT * FROM closed_dates ORDER BY closed_date ASC")
        closed = [dict(r) for r in cursor.fetchall()]

    return {
        "schedule": schedules,
        "breaks": breaks,
        "closed_dates": closed
    }

@router.put("/schedule/{day_of_week}")
def update_day_schedule(day_of_week: int, schedule: DaySchedule, current_admin: dict = Depends(get_current_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE availability_settings 
        SET is_open = ?, open_time = ?, close_time = ?, slot_interval_minutes = ?
        WHERE day_of_week = ?
        """, (1 if schedule.is_open else 0, schedule.open_time, schedule.close_time, schedule.slot_interval_minutes, day_of_week))
    return {"status": "success", "message": f"Updated schedule for {schedule.day_name}"}

@router.post("/breaks")
def add_break(item: BreakTimeItem, current_admin: dict = Depends(get_current_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO break_times (day_of_week, label, start_time, end_time)
        VALUES (?, ?, ?, ?)
        """, (item.day_of_week, item.label, item.start_time, item.end_time))
        new_id = cursor.lastrowid
    return {"status": "success", "id": new_id, "message": "Break added"}

@router.delete("/breaks/{break_id}")
def delete_break(break_id: int, current_admin: dict = Depends(get_current_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM break_times WHERE id = ?", (break_id,))
    return {"status": "success", "message": "Break removed"}

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
