from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any, Tuple, Optional
from app.database import get_db
from app.config import settings

def local_now() -> datetime:
    """
    Returns the salon's current wall-clock time.
    Uses the configured SALON_TIMEZONE (default Asia/Beirut) so that the
    "today" / "at least 30 minutes in the future" checks match the salon's
    calendar even when the server container runs in UTC. Falls back to the
    server's system time if the tz database is unavailable.
    """
    tz_name = getattr(settings, "SALON_TIMEZONE", "") or ""
    if tz_name:
        try:
            from zoneinfo import ZoneInfo
            return datetime.now(ZoneInfo(tz_name))
        except Exception:
            pass
    return datetime.now()

def time_str_to_minutes(t_str: str) -> int:
    """Converts 'HH:MM' string to minutes since midnight."""
    parts = t_str.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time format: {t_str!r}")
    h, m = int(parts[0]), int(parts[1])
    if not (0 <= h <= 23):
        raise ValueError(f"Invalid hour in time: {t_str!r}")
    if not (0 <= m <= 59):
        raise ValueError(f"Invalid minute in time: {t_str!r}")
    return h * 60 + m

def minutes_to_time_str(minutes: int) -> str:
    """Converts minutes since midnight to 'HH:MM' string."""
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"

def check_intervals_overlap(start1: int, end1: int, start2: int, end2: int) -> bool:
    """Returns True if [start1, end1) overlaps with [start2, end2)."""
    return max(start1, start2) < min(end1, end2)

def _slots_for_date(cursor, date_str: str, duration_minutes: int):
    """
    Core availability calculation executed against a *provided* cursor so callers
    can re-use an existing (locked) transaction. Returns:
        (available: bool, reason: Optional[str], slots: List[str])
    """
    try:
        req_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return False, "Invalid date format. Expected YYYY-MM-DD.", []

    now = local_now()
    today = now.date()

    if req_date < today:
        return False, "Cannot book appointments in the past.", []

    # 1. Check closed dates / holidays
    cursor.execute("SELECT reason FROM closed_dates WHERE closed_date = ?", (date_str,))
    closed_row = cursor.fetchone()
    if closed_row:
        return False, f"Salon is closed on this date: {closed_row['reason']}", []

    # 2. Check weekly schedule (0 = Monday, 6 = Sunday)
    day_of_week = req_date.weekday()
    cursor.execute(
        "SELECT is_open, open_time, close_time, slot_interval_minutes FROM availability_settings WHERE day_of_week = ?", 
        (day_of_week,)
    )
    schedule_row = cursor.fetchone()
    if not schedule_row or not schedule_row["is_open"]:
        return False, "Salon is closed on this day of the week.", []

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
        return True, "All appointments are booked for this date. Please select another date.", []

    return True, None, candidate_slots

def get_available_slots_for_date(
    date_str: str, 
    duration_minutes: int = 60,
    service_id: int = None
) -> Dict[str, Any]:
    """
    Calculates all available appointment slots for a given date and service duration.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        available, reason, slots = _slots_for_date(cursor, date_str, duration_minutes)

    return {
        "available": available,
        "slots": slots,
        "reason": reason
    }

def is_slot_available(date_str: str, time_str: str, duration_minutes: int) -> bool:
    """
    Checks if a specific start time and duration are free (uses its own connection).
    Mainly kept for backwards compatibility / public slot validation.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        available, reason, slots = _slots_for_date(cursor, date_str, duration_minutes)
    if not available:
        return False
    return time_str in slots

def is_slot_available_for_booking(cursor, date_str: str, time_str: str, duration_minutes: int) -> Tuple[bool, Optional[str]]:
    """
    Validates a specific booking request against the *given* cursor so the check and
    the insert can live inside the exact same transaction (atomic double-booking guard).
    Returns (available, reason).
    """
    available, reason, slots = _slots_for_date(cursor, date_str, duration_minutes)
    if not available:
        return False, reason or "This appointment slot is not available."
    if time_str not in slots:
        return False, "Sorry, this appointment slot is no longer available. Please select another time or date."
    return True, None
