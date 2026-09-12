from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any, Tuple
from app.database import get_db

def time_str_to_minutes(t_str: str) -> int:
    """Converts 'HH:MM' string to minutes since midnight."""
    parts = t_str.strip().split(":")
    return int(parts[0]) * 60 + int(parts[1])

def minutes_to_time_str(minutes: int) -> str:
    """Converts minutes since midnight to 'HH:MM' string."""
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"

def check_intervals_overlap(start1: int, end1: int, start2: int, end2: int) -> bool:
    """Returns True if [start1, end1) overlaps with [start2, end2)."""
    return max(start1, start2) < min(end1, end2)

def get_available_slots_for_date(
    date_str: str, 
    duration_minutes: int = 60,
    service_id: int = None
) -> Dict[str, Any]:
    """
    Calculates all available appointment slots for a given date and service duration.
    """
    try:
        req_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return {"available": False, "slots": [], "reason": "Invalid date format. Expected YYYY-MM-DD."}

    now = datetime.now()
    today = now.date()

    if req_date < today:
        return {"available": False, "slots": [], "reason": "Cannot book appointments in the past."}

    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Check closed dates / holidays
        cursor.execute("SELECT reason FROM closed_dates WHERE closed_date = ?", (date_str,))
        closed_row = cursor.fetchone()
        if closed_row:
            return {
                "available": False, 
                "slots": [], 
                "reason": f"Salon is closed on this date: {closed_row['reason']}"
            }

        # 2. Check weekly schedule (0 = Monday, 6 = Sunday)
        day_of_week = req_date.weekday()
        cursor.execute(
            "SELECT is_open, open_time, close_time, slot_interval_minutes FROM availability_settings WHERE day_of_week = ?", 
            (day_of_week,)
        )
        schedule_row = cursor.fetchone()
        if not schedule_row or not schedule_row["is_open"]:
            return {
                "available": False, 
                "slots": [], 
                "reason": "Salon is closed on this day of the week."
            }

        open_time_str = schedule_row["open_time"]
        close_time_str = schedule_row["close_time"]
        step_minutes = schedule_row["slot_interval_minutes"] or 30

        open_minutes = time_str_to_minutes(open_time_str)
        close_minutes = time_str_to_minutes(close_time_str)

        # 3. Retrieve breaks for this day of week
        cursor.execute(
            "SELECT start_time, end_time, label FROM break_times WHERE day_of_week = ?",
            (day_of_week,)
        )
        breaks = [
            (time_str_to_minutes(row["start_time"]), time_str_to_minutes(row["end_time"]))
            for row in cursor.fetchall()
        ]

        # 4. Retrieve existing non-cancelled bookings for this date
        cursor.execute(
            """
            SELECT appointment_time, duration_minutes 
            FROM bookings 
            WHERE appointment_date = ? AND status != 'cancelled'
            """,
            (date_str,)
        )
        existing_bookings = [
            (
                time_str_to_minutes(row["appointment_time"]), 
                time_str_to_minutes(row["appointment_time"]) + int(row["duration_minutes"])
            )
            for row in cursor.fetchall()
        ]

        # 5. Generate candidate start slots
        candidate_slots = []
        current_time_slot = open_minutes

        # If booking for today, earliest slot must be at least 30 minutes in the future
        min_allowed_minutes_today = None
        if req_date == today:
            min_allowed_minutes_today = now.hour * 60 + now.minute + 30

        while current_time_slot + duration_minutes <= close_minutes:
            slot_end = current_time_slot + duration_minutes

            # Check if today and slot is in the past or too soon
            if min_allowed_minutes_today and current_time_slot < min_allowed_minutes_today:
                current_time_slot += step_minutes
                continue

            # Check break overlaps
            overlaps_break = False
            for b_start, b_end in breaks:
                if check_intervals_overlap(current_time_slot, slot_end, b_start, b_end):
                    overlaps_break = True
                    break

            if overlaps_break:
                current_time_slot += step_minutes
                continue

            # Check existing booking overlaps
            overlaps_booking = False
            for b_start, b_end in existing_bookings:
                if check_intervals_overlap(current_time_slot, slot_end, b_start, b_end):
                    overlaps_booking = True
                    break

            if not overlaps_booking:
                candidate_slots.append(minutes_to_time_str(current_time_slot))

            current_time_slot += step_minutes

        if not candidate_slots:
            return {
                "available": True,
                "slots": [],
                "reason": "All appointments are booked for this date. Please select another date."
            }

        return {
            "available": True,
            "slots": candidate_slots,
            "reason": None
        }

def is_slot_available(date_str: str, time_str: str, duration_minutes: int) -> bool:
    """
    Checks if a specific start time and duration are free (used for atomic booking insertion).
    """
    res = get_available_slots_for_date(date_str, duration_minutes)
    if not res.get("available"):
        return False
    return time_str in res.get("slots", [])
