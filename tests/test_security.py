import time
import pytest
from fastapi.testclient import TestClient

# The client fixture is provided by conftest.py


def test_login_rate_limit(client: TestClient):
    """Exceeding 5 login attempts per minute should return 429."""
    payload = {"username": "admin", "password": "wrong"}
    for i in range(5):
        resp = client.post("/api/auth/login", json=payload)
        assert resp.status_code == 401  # unauthorized but not rate limited yet
    # 6th attempt should be rate limited
    resp = client.post("/api/auth/login", json=payload)
    assert resp.status_code == 429
    assert "rate limit" in resp.text.lower() or "too many requests" in resp.text.lower()


def test_booking_creation_rate_limit(client: TestClient):
    """Creating bookings limited to 30 per minute."""
    # Need a valid service and slot; use existing test helpers
    from tests.test_api import get_next_weekday, get_active_service, choose_free_slot
    date_str = get_next_weekday(1)  # Tuesday
    service = get_active_service()
    slot = choose_free_slot(date_str, service["id"])
    payload = {
        "service_id": service["id"],
        "customer_name": "Rate Limit Test",
        "customer_phone": "+961 70 000 000",
        "customer_email": "rate@example.com",
        "notes": "Rate limit test",
        "appointment_date": date_str,
        "appointment_time": slot,
    }
    # First 30 should succeed (201) or conflict if slot taken; we just ensure not 429
    for i in range(30):
        resp = client.post("/api/bookings", json=payload)
        # Could be 409 if slot already taken after first, that's fine
        assert resp.status_code != 429
    # 31st should be rate limited
    resp = client.post("/api/bookings", json=payload)
    assert resp.status_code == 429


def test_availability_rate_limit(client: TestClient):
    """Availability endpoint limited to 60 per minute."""
    from tests.test_api import get_next_weekday, get_active_service
    date_str = get_next_weekday(1)
    service = get_active_service()
    for i in range(60):
        resp = client.get(f"/api/availability/slots?date={date_str}&service_id={service['id']}")
        assert resp.status_code != 429
    resp = client.get(f"/api/availability/slots?date={date_str}&service_id={service['id']}")
    assert resp.status_code == 429


def test_double_booking_prevented(client: TestClient):
    """Two customers cannot book the exact same slot."""
    from tests.test_api import get_next_weekday, get_active_service, choose_free_slot
    date_str = get_next_weekday(2)  # Wednesday
    service = get_active_service()
    slot = choose_free_slot(date_str, service["id"])
    payload1 = {
        "service_id": service["id"],
        "customer_name": "Alice",
        "customer_phone": "+961 70 111 111",
        "customer_email": "alice@example.com",
        "appointment_date": date_str,
        "appointment_time": slot,
    }
    payload2 = payload1.copy()
    payload2["customer_name"] = "Bob"
    payload2["customer_phone"] = "+961 70 222 222"
    payload2["customer_email"] = "bob@example.com"

    r1 = client.post("/api/bookings", json=payload1)
    assert r1.status_code == 201
    r2 = client.post("/api/bookings", json=payload2)
    assert r2.status_code == 409
    assert "available" in r2.json().get("detail", "").lower() or "conflict" in r2.json().get("detail", "").lower()


def test_unauthenticated_admin_endpoints_blocked(client: TestClient):
    """Admin-only endpoints must reject unauthenticated requests."""
    endpoints = [
        ("GET", "/api/bookings"),
        ("GET", "/api/bookings/stats/overview"),
        ("POST", "/api/services"),
        ("PUT", "/api/services/1"),
        ("DELETE", "/api/services/1"),
    ]
    for method, url in endpoints:
        func = getattr(client, method.lower())
        resp = func(url)
        assert resp.status_code in (401, 403), f"{method} {url} should require auth"


def test_invalid_jwt_rejected(client: TestClient):
    """Requests with malformed/expired JWT must be rejected."""
    headers = {"Authorization": "Bearer invalid.token.here"}
    resp = client.get("/api/bookings", headers=headers)
    assert resp.status_code in (401, 403)


def test_booking_status_transition_validation(client: TestClient):
    """Only allowed status transitions are accepted."""
    # Create a booking first
    from tests.test_api import get_next_weekday, get_active_service, choose_free_slot
    date_str = get_next_weekday(3)  # Thursday
    service = get_active_service()
    slot = choose_free_slot(date_str, service["id"])
    payload = {
        "service_id": service["id"],
        "customer_name": "Status Test",
        "customer_phone": "+961 70 333 333",
        "customer_email": "status@example.com",
        "appointment_date": date_str,
        "appointment_time": slot,
    }
    create_res = client.post("/api/bookings", json=payload)
    assert create_res.status_code == 201
    booking = create_res.json()
    booking_id = booking["id"]

    # Login as admin
    login = client.post("/api/auth/login", json={"username": "admin", "password": "TestAdminPass123!"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Invalid status
    resp = client.patch(f"/api/bookings/{booking_id}/status", json={"status": "invalid"}, headers=auth_headers)
    assert resp.status_code == 400

    # Valid transition pending -> confirmed (booking may already be confirmed on creation)
    # Just ensure endpoint works for a valid status
    resp = client.patch(f"/api/bookings/{booking_id}/status", json={"status": "confirmed"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"