from typing import List
from fastapi import APIRouter, HTTPException, Depends, Query
from app.database import get_db
from app.auth import get_current_admin
from app.models import LocationCreate, LocationUpdate, LocationResponse

router = APIRouter(prefix="/api/locations", tags=["locations"])


@router.get("", response_model=List[LocationResponse])
def get_locations(include_inactive: bool = Query(False)):
    with get_db() as conn:
        cursor = conn.cursor()
        if include_inactive:
            cursor.execute("SELECT * FROM locations ORDER BY display_order ASC, id ASC")
        else:
            cursor.execute("SELECT * FROM locations WHERE is_active = TRUE ORDER BY display_order ASC, id ASC")
        return [dict(r) for r in cursor.fetchall()]


@router.post("", response_model=LocationResponse)
def create_location(item: LocationCreate, current_admin: dict = Depends(get_current_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM locations WHERE slug = ?", (item.slug,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="A location with this slug already exists.")
        cursor.execute("""
        INSERT INTO locations (slug, name, address, google_maps_url, latitude, longitude, display_order, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item.slug, item.name, item.address, item.google_maps_url,
            item.latitude, item.longitude, item.display_order, item.is_active
        ))
        cursor.execute("SELECT * FROM locations WHERE id = ?", (cursor.lastrowid,))
        return dict(cursor.fetchone())


@router.put("/{location_id}", response_model=LocationResponse)
def update_location(location_id: int, item: LocationUpdate, current_admin: dict = Depends(get_current_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM locations WHERE id = ?", (location_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Location not found.")

        updates = []
        params = []
        for field, value in item.model_dump(exclude_unset=True).items():
            updates.append(f"{field} = ?")
            params.append(value)
        if updates:
            params.append(location_id)
            cursor.execute(f"UPDATE locations SET {', '.join(updates)} WHERE id = ?", params)

        cursor.execute("SELECT * FROM locations WHERE id = ?", (location_id,))
        return dict(cursor.fetchone())


@router.delete("/{location_id}")
def delete_location(location_id: int, current_admin: dict = Depends(get_current_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM locations WHERE id = ?", (location_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Location not found.")
        cursor.execute("UPDATE locations SET is_active = FALSE WHERE id = ?", (location_id,))
    return {"status": "success", "message": "Location deactivated"}