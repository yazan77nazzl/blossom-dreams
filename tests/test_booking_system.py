import os
import pathlib
import tempfile

# Route tests to an isolated temporary database (same one used by test_api.py) so
# the live dev DB is never mutated. Because both test modules point at the same
# temp DB and initialise + seed it at import time, the suite stays deterministic
# regardless of the order pytest collects the files.
_TEST_DB = pathlib.Path(tempfile.gettempdir()) / "blossom_dreams_test.db"
for _ext in ("", "-wal", "-shm"):
    _p = pathlib.Path(str(_TEST_DB) + _ext)
    if _p.exists():
        _p.unlink()
os.environ["DATABASE_URL"] = "sqlite:///" + _TEST_DB.as_posix()

import pytest
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db
from app.seed_data import seed_database

# Ensure database is initialised and seeded before testing
init_db()
seed_database()

client = TestClient(app)

ADMIN_USER = {"username": "admin", "password": "BlossomAdmin2025!"}


def get_admin_headers():
    res = client.post("/api/auth/login", json=ADMIN_USER)
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def get_next_weekday(target_weekday: int) -> str:
    today = date.today()
    days_ahead = target_weekday - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return (today + timedelta(days=days_ahead)).isoformat()


def get_safe_weekday(target_weekday: int) -> str:
    """Like get_next_weekday but 7 days later, so the day stays free from other
    bookings made by earlier integration tests that reuse the next occurrence."""
    d = date.fromisoformat(get_next_weekday(target_weekday))
    return (d + timedelta(days=7)).isoformat()


def get_active_service() -> dict:
    services = client.get("/api/services").json()
    active = [s for s in services if s.get("is_active", True)]
    assert active, "No active services available"
    return active[0]


def choose_free_slot(date_str: str, service_id: int) -> str:
    res = client.get(f"/api/availability/slots?date={date_str}&service_id={service_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["available"] is True and data["slots"], f"No free slots on {date_str}"
    return data["slots"][0]


def booking_payload(service, slot, phone, name="Test Client") -> dict:
    return {
        "service_id": service["id"],
        "customer_name": name,
        "customer_phone": phone,
        "customer_email": "test@example.com",
        "notes": "Booking system test",
        "appointment_date": slot["date"],
        "appointment_time": slot["time"],
    }


# --- Core flow: public booking -> verification -> admin management ---
def test_complete_booking_lifecycle():
    tue = get_next_weekday(1)  # Tuesday (open day)
    service = get_active_service()
    free_slot = choose_free_slot(tue, service["id"])
    payload = {
        "service_id": service["id"],
        "customer_name": "Maya Haddad",
        "customer_phone": "+961 70 123 123",
        "customer_email": "maya@example.com",
        "notes": "Bridal consultation",
        "appointment_date": tue,
        "appointment_time": free_slot,
    }

    create_res = client.post("/api/bookings", json=payload)
    assert create_res.status_code == 201
    booking = create_res.json()
    assert booking["booking_code"].startswith("BD-")
    assert len(booking["booking_code"]) >= 5
    assert booking["status"] == "confirmed"
    assert booking["customer_name"] == "Maya Haddad"
    assert booking["appointment_date"] == tue
    assert booking["appointment_time"] == free_slot

    # Public verification endpoint
    verify_res = client.get(f"/api/bookings/verify/{booking['booking_code']}")
    assert verify_res.status_code == 200
    assert verify_res.json()["customer_name"] == "Maya Haddad"

    headers = get_admin_headers()

    # Admin list shows the new booking
    list_res = client.get("/api/bookings", headers=headers)
    assert list_res.status_code == 200
    codes = [b["booking_code"] for b in list_res.json()]
    assert booking["booking_code"] in codes

    # Admin flips status to completed
    patch_res = client.patch(
        f"/api/bookings/{booking['id']}/status",
        json={"status": "completed"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "completed"

    # Verify endpoint reflects the new status
    verify_res = client.get(f"/api/bookings/verify/{booking['booking_code']}")
    assert verify_res.json()["status"] == "completed"

    # Admin cancels -> soft delete
    cancel_res = client.delete(f"/api/bookings/{booking['id']}", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "success"


# --- Availability edge cases ---
def test_booking_rejected_on_closed_day():
    sunday = get_next_weekday(6)
    service = get_active_service()
    payload = booking_payload(service, {"date": sunday, "time": "11:00"}, "+961 70 234 234", "Closed Day Client")
    res = client.post("/api/bookings", json=payload)
    assert res.status_code == 409
    assert "closed" in res.json()["detail"].lower()


def test_booking_rejected_in_past():
    past = (date.today() - timedelta(days=3)).isoformat()
    service = get_active_service()
    payload = booking_payload(service, {"date": past, "time": "11:00"}, "+961 70 345 345", "Past Date Client")
    res = client.post("/api/bookings", json=payload)
    assert res.status_code == 409
    assert "past" in res.json()["detail"].lower()


def test_booking_rejected_during_lunch_break():
    tue = get_next_weekday(1)
    service = get_active_service()
    payload = booking_payload(service, {"date": tue, "time": "13:30"}, "+961 70 456 456", "Lunch Break Client")
    res = client.post("/api/bookings", json=payload)
    assert res.status_code == 409


def test_back_to_back_bookings_both_succeed():
    wed = get_next_weekday(2)
    service = get_active_service()
    res = client.get(f"/api/availability/slots?date={wed}&service_id={service['id']}")
    data = res.json()
    assert len(data["slots"]) >= 2, "Expected at least two independent slots"

    slot_a = data["slots"][0]
    pay_a = booking_payload(service, {"date": wed, "time": slot_a}, "+961 70 567 567", "Client A")
    assert client.post("/api/bookings", json=pay_a).status_code == 201

    # Re-fetch availability: the engine now guarantees the remaining slots do
    # not overlap with the booking just created.
    res2 = client.get(f"/api/availability/slots?date={wed}&service_id={service['id']}")
    slot_b = res2.json()["slots"][0]
    pay_b = booking_payload(service, {"date": wed, "time": slot_b}, "+961 70 678 678", "Client B")
    assert client.post("/api/bookings", json=pay_b).status_code == 201


def test_duplicate_submission_rejected():
    thu = get_next_weekday(3)
    service = get_active_service()
    free_slot = choose_free_slot(thu, service["id"])
    payload = booking_payload(service, {"date": thu, "time": free_slot}, "+961 70 789 789", "Repeat Client")

    assert client.post("/api/bookings", json=payload).status_code == 201

    # Identical request (same phone + service + slot) within minutes -> 409
    dup = client.post("/api/bookings", json=payload)
    assert dup.status_code == 409


# --- Payload validation ---
def test_malformed_payloads_rejected():
    thu = get_next_weekday(3)
    service = get_active_service()

    base = {
        "service_id": service["id"],
        "customer_name": "Validation Client",
        "customer_phone": "+961 70 999 999",
        "appointment_date": thu,
        "appointment_time": "11:00",
    }

    cases = [
        ("bad date format", {**base, "appointment_date": "2026/01/15"}, 422),
        ("bad time format", {**base, "appointment_time": "9:05"}, 422),
        ("bad email", {**base, "customer_email": "not-an-email"}, 422),
        ("name too short", {**base, "customer_name": "A"}, 422),
        ("phone too short", {**base, "customer_phone": "12"}, 422),
        ("whitespace-only name", {**base, "customer_name": "   "}, 400),
        ("whitespace-only phone", {**base, "customer_phone": "     "}, 400),
        ("time 25:00", {**base, "appointment_time": "25:00"}, 400),
    ]

    for label, payload, expected in cases:
        res = client.post("/api/bookings", json=payload)
        assert res.status_code == expected, f"{label}: expected {expected}, got {res.status_code}"


def test_invalid_status_literal_rejected():
    headers = get_admin_headers()
    bad = client.patch("/api/bookings/1/status", json={"status": "not-a-status"}, headers=headers)
    assert bad.status_code == 422


# --- Authorization guards ---
def test_private_endpoints_require_auth():
    assert client.get("/api/bookings").status_code == 401
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/bookings/stats/overview").status_code == 401
    assert client.patch("/api/bookings/1/status", json={"status": "confirmed"}).status_code == 401
    assert client.delete("/api/bookings/1").status_code == 401


# --- Race condition: exactly one booking survives concurrent submission ---
def test_concurrent_double_booking_only_one_succeeds():
    fri = get_next_weekday(4)
    service = get_active_service()
    free_slot = choose_free_slot(fri, service["id"])

    def attempt(phone):
        payload = {
            "service_id": service["id"],
            "customer_name": "Race Client",
            "customer_phone": phone,
            "customer_email": "race@example.com",
            "appointment_date": fri,
            "appointment_time": free_slot,
        }
        return client.post("/api/bookings", json=payload).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ["+961 70 111 222", "+961 70 222 333"]))

    assert sorted(results) == [201, 409], f"Expected exactly one success and one conflict, got {results}"


# --- Opening-hours boundaries ---
def _add_minutes(time_str: str, minutes: int) -> str:
    h, m = (int(x) for x in time_str.split(":"))
    total = h * 60 + m + minutes
    return f"{total // 60:02d}:{total % 60:02d}"


def test_booking_before_opening_hours_rejected():
    tue = get_next_weekday(1)  # Opens 09:00
    service = get_active_service()
    payload = booking_payload(service, {"date": tue, "time": "08:00"}, "+961 70 801 801", "Early Bird Client")
    res = client.post("/api/bookings", json=payload)
    assert res.status_code == 409


def test_booking_after_closing_hours_rejected():
    tue = get_next_weekday(1)  # Closes 19:00
    service = get_active_service()
    payload = booking_payload(service, {"date": tue, "time": "23:00"}, "+961 70 802 802", "Night Owl Client")
    res = client.post("/api/bookings", json=payload)
    assert res.status_code == 409
    assert "slot" in res.json()["detail"].lower()


def test_booking_adjacent_to_midday_break_blocked():
    # The break runs 13:30-14:30; any start overlapping it must be rejected.
    tue = get_next_weekday(1)
    service = get_active_service()
    cases = {
        "13:00": "+961 70 816 816",  # ends 14:00, inside the break
        "13:45": "+961 70 817 817",  # starts mid-break
        "14:00": "+961 70 818 818",  # starts exactly as the break ends
    }
    for start, phone in cases.items():
        payload = booking_payload(service, {"date": tue, "time": start}, phone, "Break Client")
        res = client.post("/api/bookings", json=payload)
        assert res.status_code == 409, f"{start} should be blocked by the lunch break"


# --- Service state edge cases ---
def test_nonexistent_service_rejected():
    thu = get_next_weekday(3)
    payload = booking_payload({"id": 999999, "duration_minutes": 60}, {"date": thu, "time": "11:00"}, "+961 70 803 803", "Ghost Service Client")
    res = client.post("/api/bookings", json=payload)
    assert res.status_code == 400


def test_inactive_service_rejected():
    headers = get_admin_headers()
    cat_id = client.get("/api/categories").json()[0]["id"]

    create_res = client.post("/api/services", headers=headers, json={
        "category_id": cat_id,
        "name": "Inactive Edge Test Service",
        "slug": "inactive-edge-test-service",
        "duration_minutes": 60,
        "price": 30.0,
        "is_active": False,
    })
    assert create_res.status_code == 200
    service_id = create_res.json()["id"]

    try:
        fri = get_next_weekday(4)
        payload = booking_payload(
            {"id": service_id, "duration_minutes": 60},
            {"date": fri, "time": "11:00"},
            "+961 70 804 804",
            "Inactive Service Client",
        )
        res = client.post("/api/bookings", json=payload)
        assert res.status_code == 400
        assert "available" in res.json()["detail"].lower()
    finally:
        client.delete(f"/api/services/{service_id}", headers=headers)


def test_holiday_closed_date_rejected_and_removed():
    headers = get_admin_headers()
    sat = get_next_weekday(5)
    service = get_active_service()

    add_res = client.post("/api/availability/closed-dates", headers=headers,
                          json={"closed_date": sat, "reason": "Private event"})
    assert add_res.status_code == 200
    closed_id = add_res.json()["id"]

    try:
        payload = booking_payload(service, {"date": sat, "time": "11:00"}, "+961 70 805 805", "Holiday Client")
        res = client.post("/api/bookings", json=payload)
        assert res.status_code == 409
        assert "closed" in res.json()["detail"].lower()
    finally:
        del_res = client.delete(f"/api/availability/closed-dates/{closed_id}", headers=headers)
        assert del_res.status_code == 200
        # Confirm the date is now bookable again
        avail = client.get(f"/api/availability/slots?date={sat}&service_id={service['id']}").json()
        assert avail["available"] is True


# --- Slot freedom / cancellation ---
def test_cancelled_booking_frees_slot():
    mon = get_next_weekday(0)
    service = get_active_service()
    free_slot = choose_free_slot(mon, service["id"])
    headers = get_admin_headers()

    create_res = client.post("/api/bookings", json=booking_payload(
        service, {"date": mon, "time": free_slot}, "+961 70 806 806", "Cancel Me Client"))
    assert create_res.status_code == 201
    booking_id = create_res.json()["id"]

    cancel_res = client.delete(f"/api/bookings/{booking_id}", headers=headers)
    assert cancel_res.status_code == 200

    # The slot must be offered again and re-bookable by a different client.
    avail_slots = client.get(f"/api/availability/slots?date={mon}&service_id={service['id']}").json()["slots"]
    assert free_slot in avail_slots
    rebook = client.post("/api/bookings", json=booking_payload(
        service, {"date": mon, "time": free_slot}, "+961 70 807 807", "Replacement Client"))
    assert rebook.status_code == 201


# --- Duration / overlap invariants ---
def test_overlapping_duration_blocked_adjacent_allowed():
    services = client.get("/api/services").json()
    s90 = next(s for s in services if s["slug"] == "gel-sculpted-extensions")
    s60 = next(s for s in services if s["slug"] == "russian-manicure")
    thu = get_next_weekday(3)

    start = choose_free_slot(thu, s90["id"])
    long_payload = booking_payload(s90, {"date": thu, "time": start}, "+961 70 808 808", "Long Service Client")
    assert client.post("/api/bookings", json=long_payload).status_code == 201

    # A 60-min booking starting inside the 90-min appointment must conflict.
    inside = _add_minutes(start, 60)
    overlap_payload = booking_payload(s60, {"date": thu, "time": inside}, "+961 70 809 809", "Overlap Client")
    res = client.post("/api/bookings", json=overlap_payload)
    assert res.status_code == 409

    # A 60-min booking starting exactly when the 90-min one ends is fine.
    adjacent = _add_minutes(start, 90)
    adjacent_payload = booking_payload(s60, {"date": thu, "time": adjacent}, "+961 70 810 810", "Adjacent Client")
    res2 = client.post("/api/bookings", json=adjacent_payload)
    assert res2.status_code == 201, res2.text


def test_double_booking_different_services_same_slot_conflicts():
    services = client.get("/api/services").json()
    s_a = next(s for s in services if s["slug"] == "russian-manicure")
    s_b = next(s for s in services if s["slug"] == "deluxe-spa-pedicure")
    wed = get_next_weekday(2)

    slot = choose_free_slot(wed, s_a["id"])
    first = booking_payload(s_a, {"date": wed, "time": slot}, "+961 70 811 811", "First Client")
    assert client.post("/api/bookings", json=first).status_code == 201

    second = booking_payload(s_b, {"date": wed, "time": slot}, "+961 70 812 812", "Second Client")
    res = client.post("/api/bookings", json=second)
    assert res.status_code == 409


# --- Payload limits & optional fields ---
def test_notes_length_limit_enforced():
    thu = get_next_weekday(3)
    service = get_active_service()
    payload = booking_payload(service, {"date": thu, "time": "11:00"}, "+961 70 813 813", "Notes Client")
    payload["notes"] = "x" * 1001
    res = client.post("/api/bookings", json=payload)
    assert res.status_code == 422


def test_email_optional():
    mon = get_next_weekday(0)
    service = get_active_service()
    slot = choose_free_slot(mon, service["id"])
    payload = booking_payload(service, {"date": mon, "time": slot}, "+961 70 814 814", "No Email Client")
    payload.pop("customer_email")
    res = client.post("/api/bookings", json=payload)
    assert res.status_code == 201
    assert res.json()["customer_email"] is None


# --- Lookup & admin filtering ---
def test_verify_booking_nonexistent_code_404():
    res = client.get("/api/bookings/verify/BD-XXXXX")
    assert res.status_code == 404


def test_admin_booking_search_filter():
    mon = get_next_weekday(0)
    service = get_active_service()
    slot = choose_free_slot(mon, service["id"])
    special_name = f"Zelda Search Target {date.today().isoformat().replace('-', '')}"
    created = client.post("/api/bookings", json=booking_payload(
        service, {"date": mon, "time": slot}, "+961 70 815 815", special_name))
    assert created.status_code == 201

    headers = get_admin_headers()
    res = client.get("/api/bookings", params={"search": "Zelda Search Target"}, headers=headers)
    assert res.status_code == 200
    rows = res.json()
    assert rows, "Search should return at least one booking"
    for b in rows:
        assert "zelda" in b["customer_name"].lower() or "zelda" in (b["customer_phone"] or "").lower()


# --- Configured opening hours are honoured (no hardcoded 09:00 / 12:00) ---
def test_open_day_first_slot_matches_configured_open_time():
    tue = get_safe_weekday(1)
    service = get_active_service()
    res = client.get(f"/api/availability/slots?date={tue}&service_id={service['id']}")
    assert res.status_code == 200
    data = res.json()
    assert data["available"] is True and data["slots"]
    assert data["slots"][0] == "09:00", f"First slot must be the configured 09:00 opening, got {data['slots'][0]}"


def test_booking_at_morning_slots_0900_1200_all_succeed():
    services = client.get("/api/services").json()
    service = next(s for s in services if s["slug"] == "russian-manicure")  # 60-min
    wed = get_safe_weekday(2)
    slots_res = client.get(f"/api/availability/slots?date={wed}&service_id={service['id']}").json()
    openings = {"09:00", "10:00", "11:00", "12:00"}
    missing = openings - set(slots_res["slots"])
    assert not missing, f"Morning slots missing from availability: {sorted(missing)}"

    for i, t in enumerate(sorted(openings)):
        payload = booking_payload(service, {"date": wed, "time": t}, f"+961 70 830 8{i}", f"Morning Client {t[:5]}")
        assert client.post("/api/bookings", json=payload).status_code == 201, f"Booking at {t} should succeed"


def test_slots_follow_configured_open_time_close_not_hardcoded():
    headers = get_admin_headers()
    day = 3  # Thursday
    config = client.get("/api/availability/config").json()
    original = next(s for s in config["schedule"] if s["day_of_week"] == day)
    service = get_active_service()

    try:
        put = client.put(f"/api/availability/schedule/{day}", headers=headers, json={
            "day_of_week": day,
            "day_name": original["day_name"],
            "is_open": True,
            "open_time": "11:00",
            "close_time": original["close_time"],
            "slot_interval_minutes": original["slot_interval_minutes"],
        })
        assert put.status_code == 200

        thu = get_safe_weekday(day)
        res = client.get(f"/api/availability/slots?date={thu}&service_id={service['id']}")
        data = res.json()
        assert data["available"] is True and data["slots"]
        assert data["slots"][0] == "11:00", f"Slots must start at the configured 11:00, got {data['slots'][0]}"
        assert "09:00" not in data["slots"]
        assert "10:00" not in data["slots"]

        # A booking at the new opening hour succeeds; one before opening is rejected
        ok = client.post("/api/bookings", json=booking_payload(
            service, {"date": thu, "time": "11:00"}, "+961 70 831 831", "Late Open Client"))
        assert ok.status_code == 201

        blocked = client.post("/api/bookings", json=booking_payload(
            service, {"date": thu, "time": "09:00"}, "+961 70 832 832", "Too Early Client"))
        assert blocked.status_code == 409
    finally:
        client.put(f"/api/availability/schedule/{day}", headers=headers, json={
            "day_of_week": day,
            "day_name": original["day_name"],
            "is_open": True,
            "open_time": original["open_time"],
            "close_time": original["close_time"],
            "slot_interval_minutes": original["slot_interval_minutes"],
        })


def test_slot_interval_respected_not_hardcoded_30():
    headers = get_admin_headers()
    day = 4  # Friday
    config = client.get("/api/availability/config").json()
    original = next(s for s in config["schedule"] if s["day_of_week"] == day)
    service = get_active_service()

    try:
        put = client.put(f"/api/availability/schedule/{day}", headers=headers, json={
            "day_of_week": day,
            "day_name": original["day_name"],
            "is_open": True,
            "open_time": original["open_time"],
            "close_time": original["close_time"],
            "slot_interval_minutes": 60,
        })
        assert put.status_code == 200

        fri = get_safe_weekday(day)
        res = client.get(f"/api/availability/slots?date={fri}&service_id={service['id']}")
        data = res.json()
        assert data["available"] is True and data["slots"]
        slots = data["slots"]

        # Every slot starts exactly on the hour: the 30-min hardcode is gone.
        assert all(t.endswith(":00") for t in slots), f"Slots should be hourly with a 60-min interval: {slots}"

        # Spacing is 60 minutes normally and 180 only across the lunch break (13:30-14:30).
        times = [int(t[:2]) * 60 + int(t[3:]) for t in slots]
        gaps = [times[i + 1] - times[i] for i in range(len(times) - 1)]
        assert all(g == 60 or g == 180 for g in gaps), f"Unexpected slot spacing with 60-min interval: gaps {gaps}"
    finally:
        client.put(f"/api/availability/schedule/{day}", headers=headers, json={
            "day_of_week": day,
            "day_name": original["day_name"],
            "is_open": True,
            "open_time": original["open_time"],
            "close_time": original["close_time"],
            "slot_interval_minutes": original["slot_interval_minutes"],
        })


def test_availability_config_returns_configured_opening_hours():
    config = client.get("/api/availability/config").json()
    assert config["schedule"]
    monday = next(s for s in config["schedule"] if s["day_of_week"] == 0)
    assert monday["open_time"] == "09:00"
    assert monday["close_time"] == "19:00"
    assert monday["slot_interval_minutes"] == 30


# --- Business locations ---
def get_location_id(slug: str) -> int:
    locations = client.get("/api/locations").json()
    match = next(l for l in locations if l["slug"] == slug)
    return match["id"]


def get_lonely_weekday(target_weekday: int, weeks_ahead: int = 1) -> str:
    """A future weekday moved several weeks out, so it cannot collide with
    bookings created by the other location tests (each uses a distinct date)."""
    today = date.today()
    days_ahead = target_weekday - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return (today + timedelta(days=days_ahead) + timedelta(weeks=weeks_ahead)).isoformat()


def test_locations_endpoint_returns_both_seeded_locations():
    res = client.get("/api/locations")
    assert res.status_code == 200
    locations = res.json()
    slugs = {l["slug"] for l in locations}
    assert {"versailles", "amwaj"} <= slugs, f"Both seeded locations must exist, got {slugs}"

    versailles = next(l for l in locations if l["slug"] == "versailles")
    assert versailles["google_maps_url"] == "https://maps.google.com/?ftid=0x151f4096b6ee7923:0x1de97506f65318e9"
    amwaj = next(l for l in locations if l["slug"] == "amwaj")
    # Amwaj's map link is the established one and must never change.
    assert amwaj["google_maps_url"] == "https://maps.google.com/?q=Amwaj+Center+Jounieh+Lebanon"


def test_booking_stores_and_returns_location():
    versailles = get_location_id("versailles")
    amwaj = get_location_id("amwaj")
    tue = get_lonely_weekday(1, weeks_ahead=2)
    service = get_active_service()
    slots = client.get(f"/api/availability/slots?date={tue}&service_id={service['id']}&location_id={versailles}").json()
    slot = slots["slots"][0]

    payload = booking_payload(service, {"date": tue, "time": slot}, "+961 70 901 901", "Location Client")
    payload["location_id"] = amwaj
    create_res = client.post("/api/bookings", json=payload)
    assert create_res.status_code == 201
    booking = create_res.json()
    assert booking["location_id"] == amwaj
    assert booking["location_name"] == "Amwaj Center"

    # Public verification and the admin list both expose the location name
    verify = client.get(f"/api/bookings/verify/{booking['booking_code']}").json()
    assert verify["location_name"] == "Amwaj Center"

    headers = get_admin_headers()
    admin_row = next(b for b in client.get("/api/bookings", headers=headers).json() if b["id"] == booking["id"])
    assert admin_row["location_id"] == amwaj
    assert admin_row["location_name"] == "Amwaj Center"


def test_booking_rejected_for_unknown_location():
    tue = get_lonely_weekday(1, weeks_ahead=1)
    service = get_active_service()
    payload = booking_payload(service, {"date": tue, "time": "11:00"}, "+961 70 902 902", "Ghost Location Client")
    payload["location_id"] = 999999
    res = client.post("/api/bookings", json=payload)
    assert res.status_code == 400
    assert "location" in res.json()["detail"].lower()


def test_same_slot_free_at_second_location():
    versailles = get_location_id("versailles")
    amwaj = get_location_id("amwaj")
    wed = get_lonely_weekday(2, weeks_ahead=1)
    service = get_active_service()

    versailles_slots = client.get(f"/api/availability/slots?date={wed}&service_id={service['id']}&location_id={versailles}").json()["slots"]
    slot = versailles_slots[0]

    # Book it at Versailles
    v_payload = booking_payload(service, {"date": wed, "time": slot}, "+961 70 903 903", "Versailles Client")
    v_payload["location_id"] = versailles
    assert client.post("/api/bookings", json=v_payload).status_code == 201

    # Same slot must still be free at Amwaj
    amwaj_slots = client.get(f"/api/availability/slots?date={wed}&service_id={service['id']}&location_id={amwaj}").json()["slots"]
    assert slot in amwaj_slots

    a_payload = booking_payload(service, {"date": wed, "time": slot}, "+961 70 904 904", "Amwaj Client")
    a_payload["location_id"] = amwaj
    assert client.post("/api/bookings", json=a_payload).status_code == 201

    # Doubling up on the same (location, slot) is still rejected
    dup_payload = booking_payload(service, {"date": wed, "time": slot}, "+961 70 905 905", "Versailles Dupe Client")
    dup_payload["location_id"] = versailles
    assert client.post("/api/bookings", json=dup_payload).status_code == 409


def test_per_location_schedule_override_isolation():
    headers = get_admin_headers()
    versailles = get_location_id("versailles")
    amwaj = get_location_id("amwaj")
    day = 0  # Monday
    service = get_active_service()
    mon = get_lonely_weekday(day, weeks_ahead=1)

    try:
        put = client.put(f"/api/availability/schedule/{day}?location_id={versailles}", headers=headers, json={
            "day_of_week": day,
            "day_name": "Monday",
            "is_open": True,
            "open_time": "10:00",
            "close_time": "19:00",
            "slot_interval_minutes": 30,
        })
        assert put.status_code == 200

        v_slots = client.get(f"/api/availability/slots?date={mon}&service_id={service['id']}&location_id={versailles}").json()
        a_slots = client.get(f"/api/availability/slots?date={mon}&service_id={service['id']}&location_id={amwaj}").json()

        assert v_slots["slots"][0] == "10:00", f"Versailles must honor its 10:00 override, got {v_slots['slots'][0]}"
        assert a_slots["slots"][0] == "09:00", f"Amwaj must keep the global 09:00 opening, got {a_slots['slots'][0]}"

        # The config endpoint reflects the override for that location
        v_config = client.get(f"/api/availability/config?location_id={versailles}").json()
        mon_entry = next(s for s in v_config["schedule"] if s["day_of_week"] == day)
        assert mon_entry["open_time"] == "10:00"
    finally:
        client.delete(f"/api/availability/schedule/{day}/override?location_id={versailles}", headers=headers)


def test_per_location_buffer_extends_existing_booking():
    headers = get_admin_headers()
    day = 0  # Monday
    services = client.get("/api/services").json()
    service = next(s for s in services if s["slug"] == "russian-manicure")  # 60-min
    mon = get_lonely_weekday(day, weeks_ahead=3)
    config = client.get("/api/availability/config").json()
    original = next(s for s in config["schedule"] if s["day_of_week"] == day)

    try:
        put = client.put(f"/api/availability/schedule/{day}", headers=headers, json={
            "day_of_week": day,
            "day_name": original["day_name"],
            "is_open": True,
            "open_time": original["open_time"],
            "close_time": original["close_time"],
            "slot_interval_minutes": original["slot_interval_minutes"],
            "buffer_minutes": 30,
        })
        assert put.status_code == 200

        # Book 10:00 (60 min -> ends 11:00 + 30 min buffer = 11:30)
        free = client.get(f"/api/availability/slots?date={mon}&service_id={service['id']}").json()["slots"]
        assert "10:00" in free
        payload = booking_payload(service, {"date": mon, "time": "10:00"}, "+961 70 906 906", "Buffer Client")
        assert client.post("/api/bookings", json=payload).status_code == 201

        # 11:00 must now be blocked by the buffered tail; 11:30 is free again
        after = client.get(f"/api/availability/slots?date={mon}&service_id={service['id']}").json()["slots"]
        assert "11:00" not in after
        assert "11:30" in after
    finally:
        client.put(f"/api/availability/schedule/{day}", headers=headers, json={
            "day_of_week": day,
            "day_name": original["day_name"],
            "is_open": original["is_open"],
            "open_time": original["open_time"],
            "close_time": original["close_time"],
            "slot_interval_minutes": original["slot_interval_minutes"],
            "buffer_minutes": 0,
        })


def test_availability_config_buffer_save_global():
    headers = get_admin_headers()
    day = 0
    original = next(s for s in client.get("/api/availability/config").json()["schedule"] if s["day_of_week"] == day)
    original_buf = original["buffer_minutes"]

    put = client.put("/api/availability/config", headers=headers, json={"buffer_minutes": 45})
    assert put.status_code == 200

    updated = next(s for s in client.get("/api/availability/config").json()["schedule"] if s["day_of_week"] == day)
    assert updated["buffer_minutes"] == 45

    # Restore original
    client.put("/api/availability/config", headers=headers, json={"buffer_minutes": original_buf})


def test_availability_config_buffer_save_location():
    headers = get_admin_headers()
    amwaj_id = get_location_id("amwaj")
    versailles_id = get_location_id("versailles")
    day = 2  # Wednesday

    put = client.put(f"/api/availability/config?location_id={amwaj_id}", headers=headers, json={"buffer_minutes": 20})
    assert put.status_code == 200

    amwaj_config = client.get(f"/api/availability/config?location_id={amwaj_id}").json()
    amwaj_day = next(s for s in amwaj_config["schedule"] if s["day_of_week"] == day)
    assert amwaj_day["buffer_minutes"] == 20

    versailles_config = client.get(f"/api/availability/config?location_id={versailles_id}").json()
    versailles_day = next(s for s in versailles_config["schedule"] if s["day_of_week"] == day)
    assert versailles_day["buffer_minutes"] == 0