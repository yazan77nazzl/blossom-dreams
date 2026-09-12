import re
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from app.database import get_db
from app.auth import get_current_admin
from app.models import ServiceCreate, ServiceUpdate, ServiceResponse

router = APIRouter(prefix="/api/services", tags=["services"])

def slugify(text: str) -> str:
    text = text.lower().strip()
    return re.sub(r'[\s\W-]+', '-', text).strip('-')

def format_service_row(row) -> dict:
    d = dict(row)
    price = d.get("price") or 0.0
    disc = d.get("discount_price")
    if disc and price > 0 and disc < price:
        d["discount_percent"] = round(((price - disc) / price) * 100)
    else:
        d["discount_percent"] = None
    return d

@router.get("", response_model=List[ServiceResponse])
def get_services(
    category_id: Optional[int] = None,
    category_slug: Optional[str] = None,
    search: Optional[str] = None,
    featured_only: bool = False,
    include_inactive: bool = False
):
    with get_db() as conn:
        cursor = conn.cursor()
        query = """
        SELECT s.*, c.name as category_name
        FROM services s
        JOIN categories c ON s.category_id = c.id
        WHERE 1=1
        """
        params = []

        if not include_inactive:
            query += " AND s.is_active = 1 AND c.is_active = 1"

        if category_id:
            query += " AND s.category_id = ?"
            params.append(category_id)

        if category_slug:
            query += " AND c.slug = ?"
            params.append(category_slug)

        if featured_only:
            query += " AND s.is_featured = 1"

        if search:
            query += " AND (s.name LIKE ? OR s.description LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term])

        query += " ORDER BY c.display_order ASC, s.is_featured DESC, s.name ASC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [format_service_row(r) for r in rows]

@router.get("/{service_id}", response_model=ServiceResponse)
def get_service(service_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT s.*, c.name as category_name
        FROM services s
        JOIN categories c ON s.category_id = c.id
        WHERE s.id = ?
        """, (service_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Service not found")
        return format_service_row(row)

@router.post("", response_model=ServiceResponse)
def create_service(srv: ServiceCreate, current_admin: dict = Depends(get_current_admin)):
    slug = srv.slug or slugify(srv.name)
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
            INSERT INTO services (
                category_id, name, slug, description, duration_minutes,
                price, discount_price, image_url, is_active, is_featured
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                srv.category_id, srv.name, slug, srv.description, srv.duration_minutes,
                srv.price, srv.discount_price, srv.image_url,
                1 if srv.is_active else 0,
                1 if srv.is_featured else 0
            ))
            new_id = cursor.lastrowid
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to create service: {str(e)}")

        cursor.execute("""
        SELECT s.*, c.name as category_name
        FROM services s
        JOIN categories c ON s.category_id = c.id
        WHERE s.id = ?
        """, (new_id,))
        return format_service_row(cursor.fetchone())

@router.put("/{service_id}", response_model=ServiceResponse)
def update_service(service_id: int, srv: ServiceUpdate, current_admin: dict = Depends(get_current_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM services WHERE id = ?", (service_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Service not found")

        updates = []
        params = []
        if srv.category_id is not None:
            updates.append("category_id = ?")
            params.append(srv.category_id)
        if srv.name is not None:
            updates.append("name = ?")
            params.append(srv.name)
            if not srv.slug:
                updates.append("slug = ?")
                params.append(slugify(srv.name))
        if srv.slug is not None:
            updates.append("slug = ?")
            params.append(slugify(srv.slug))
        if srv.description is not None:
            updates.append("description = ?")
            params.append(srv.description)
        if srv.duration_minutes is not None:
            updates.append("duration_minutes = ?")
            params.append(srv.duration_minutes)
        if srv.price is not None:
            updates.append("price = ?")
            params.append(srv.price)
        if srv.discount_price is not None:
            updates.append("discount_price = ?")
            params.append(srv.discount_price if srv.discount_price > 0 else None)
        if srv.image_url is not None:
            updates.append("image_url = ?")
            params.append(srv.image_url)
        if srv.is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if srv.is_active else 0)
        if srv.is_featured is not None:
            updates.append("is_featured = ?")
            params.append(1 if srv.is_featured else 0)

        if updates:
            params.append(service_id)
            cursor.execute(f"UPDATE services SET {', '.join(updates)} WHERE id = ?", params)

        cursor.execute("""
        SELECT s.*, c.name as category_name
        FROM services s
        JOIN categories c ON s.category_id = c.id
        WHERE s.id = ?
        """, (service_id,))
        return format_service_row(cursor.fetchone())

@router.delete("/{service_id}")
def delete_service(service_id: int, current_admin: dict = Depends(get_current_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM services WHERE id = ?", (service_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Service not found")
        
        cursor.execute("DELETE FROM services WHERE id = ?", (service_id,))
    return {"status": "success", "message": "Service deleted"}
