import os
import pathlib
import tempfile

# Route tests to an isolated temporary database so the live dev DB is never mutated.
# This keeps the suite deterministic regardless of manual bookings made in the admin dashboard.
_TEST_DB = pathlib.Path(tempfile.gettempdir()) / "blossom_dreams_test.db"
for _ext in ("", "-wal", "-shm"):
    _p = pathlib.Path(str(_TEST_DB) + _ext)
    if _p.exists():
        _p.unlink()
os.environ["DATABASE_URL"] = "sqlite:///" + _TEST_DB.as_posix()

import pytest
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db
from app.seed_data import seed_database

# Ensure database is initialised and seeded before testing
init_db()
seed_database()

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Blossom Dreams" in data["app"]

def test_salon_settings_public():
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["salon_name"] == "BLOSSOM DREAMS"
    assert "blossomdreams.lb" in data["instagram_url"]
    assert data["currency_symbol"] == "$"

def test_categories_public():
    response = client.get("/api/categories")
    assert response.status_code == 200
    cats = response.json()
    assert len(cats) >= 5
    slugs = [c["slug"] for c in cats]
    assert "nails" in slugs
    assert "lashes" in slugs
    assert "brows" in slugs

def test_services_catalog():
    response = client.get("/api/services")
    assert response.status_code == 200
    services = response.json()
    assert len(services) >= 10
    first = services[0]
    assert "name" in first
    assert "duration_minutes" in first
    assert "price" in first
    assert first["price"] > 0

def test_special_offers():
    response = client.get("/api/offers")
    assert response.status_code == 200
    offers = response.json()
    assert len(offers) >= 1
    first = offers[0]
    assert "discounted_price" in first
    assert first["discounted_price"] < first["original_price"]
    assert first["discount_percent"] > 0

def get_next_weekday(target_weekday=1): # Default Tuesday
    today = date.today()
    days_ahead = target_weekday - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return (today + timedelta(days=days_ahead)).isoformat()

def test_availability_slots():
    next_tue = get_next_weekday(1) # Tuesday
    # Get a service
    services = client.get("/api/services").json()
    service_id = services[0]["id"]

    response = client.get(f"/api/availability/slots?date={next_tue}&service_id={service_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert len(data["slots"]) > 0
    # Breaks were removed entirely: the former 13:30-14:30 lunch block must not
    # introduce any artificial unavailability on open days.
    assert "13:30" in data["slots"]
    assert "14:00" in data["slots"]

def test_sunday_closed():
    # Next Sunday
    today = date.today()
    days_ahead = 6 - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    next_sun = (today + timedelta(days=days_ahead)).isoformat()

    response = client.get(f"/api/availability/slots?date={next_sun}")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is False
    assert "closed" in data["reason"].lower()

def test_booking_creation_and_double_booking_prevention():
    next_wed = get_next_weekday(2) # Wednesday
    services = client.get("/api/services").json()
    srv = services[0]

    # Get available slots
    slots_res = client.get(f"/api/availability/slots?date={next_wed}&service_id={srv['id']}").json()
    assert len(slots_res["slots"]) > 0
    chosen_slot = slots_res["slots"][0]

    # 1. Customer A books the slot
    booking_payload = {
        "service_id": srv["id"],
        "customer_name": "Sarah Mansour",
        "customer_phone": "+961 70 999 111",
        "customer_email": "sarah@example.com",
        "notes": "Testing automated booking flow",
        "appointment_date": next_wed,
        "appointment_time": chosen_slot
    }

    create_res = client.post("/api/bookings", json=booking_payload)
    assert create_res.status_code == 201
    booking_data = create_res.json()
    assert booking_data["booking_code"].startswith("BD-")
    assert booking_data["status"] == "confirmed"

    # 2. Customer B attempts to book the EXACT same date and time slot -> MUST BE PREVENTED
    conflict_payload = {
        "service_id": srv["id"],
        "customer_name": "Lina Khoury",
        "customer_phone": "+961 71 888 222",
        "notes": "Concurrent conflicting booking",
        "appointment_date": next_wed,
        "appointment_time": chosen_slot
    }

    conflict_res = client.post("/api/bookings", json=conflict_payload)
    assert conflict_res.status_code == 409
    assert "no longer available" in conflict_res.json()["detail"].lower() or "conflict" in conflict_res.json()["detail"].lower()

    # 3. Verify public lookup works
    verify_res = client.get(f"/api/bookings/verify/{booking_data['booking_code']}")
    assert verify_res.status_code == 200
    assert verify_res.json()["customer_name"] == "Sarah Mansour"

def test_admin_auth_and_protected_crud():
    # 1. Invalid login
    bad_login = client.post("/api/auth/login", json={"username": "admin", "password": "WrongPassword!"})
    assert bad_login.status_code == 401

    # 2. Valid login
    good_login = client.post("/api/auth/login", json={"username": "admin", "password": "BlossomAdmin2025!"})
    assert good_login.status_code == 200
    auth_data = good_login.json()
    token = auth_data["access_token"]
    assert token

    headers = {"Authorization": f"Bearer {token}"}

    # 3. GET /api/auth/me
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "admin"

    # 4. Admin Overview Stats
    stats_res = client.get("/api/bookings/stats/overview", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert "today_appointments_count" in stats
    assert "total_active_services" in stats

    # 5. Service CRUD by Admin
    cats = client.get("/api/categories").json()
    new_srv = {
        "category_id": cats[0]["id"],
        "name": "Luxury Champagne Pedicure",
        "description": "Rose champagne foot bath and diamond scrub",
        "duration_minutes": 60,
        "price": 50.0,
        "discount_price": 42.0,
        "is_active": True,
        "is_featured": False
    }
    srv_create = client.post("/api/services", json=new_srv, headers=headers)
    assert srv_create.status_code == 200
    created_srv = srv_create.json()
    assert created_srv["name"] == "Luxury Champagne Pedicure"
    assert created_srv["discount_percent"] == 16

    # Update Service
    srv_update = client.put(f"/api/services/{created_srv['id']}", json={"price": 55.0}, headers=headers)
    assert srv_update.status_code == 200
    assert srv_update.json()["price"] == 55.0

    # Delete Service
    srv_del = client.delete(f"/api/services/{created_srv['id']}", headers=headers)
    assert srv_del.status_code == 200
