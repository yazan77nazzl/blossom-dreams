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
    subcategory_id: Optional[int] = None,
    subcategory_slug: Optional[str] = None,
    search: Optional[str] = None,
    featured_only: bool = False,
    include_inactive: bool = False
):
    with get_db() as conn:
        cursor = conn.cursor()
        query = """
        SELECT s.*, c.name as category_name, sc.name as subcategory_name, sc.slug as subcategory_slug
        FROM services s
        JOIN categories c ON s.category_id = c.id
        LEFT JOIN subcategories sc ON s.subcategory_id = sc.id
        WHERE 1=1
        """
        params = []

        if not include_inactive:
            query += " AND s.is_active = TRUE AND c.is_active = TRUE"

        if category_id:
            query += " AND s.category_id = %s"
            params.append(category_id)

        if category_slug:
            query += " AND c.slug = %s"
            params.append(category_slug)

        if subcategory_id:
            query += " AND s.subcategory_id = %s"
            params.append(subcategory_id)

        if subcategory_slug:
            query += " AND sc.slug = %s"
            params.append(subcategory_slug)

        if featured_only:
            query += " AND s.is_featured = TRUE"

        if search:
            query += " AND (s.name ILIKE %s OR s.description ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term])

        query += " ORDER BY c.display_order ASC, s.is_featured DESC, s.name ASC"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        return [format_service_row(r) for r in rows]

@router.get("/{service_id}", response_model=ServiceResponse)
def get_service(service_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT s.*, c.name as category_name, sc.name as subcategory_name, sc.slug as subcategory_slug
        FROM services s
        JOIN categories c ON s.category_id = c.id
        LEFT JOIN subcategories sc ON s.subcategory_id = sc.id
        WHERE s.id = %s
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
                price, discount_price, image_url, is_active, is_featured, nail_subcategory_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                srv.category_id, srv.name, slug, srv.description, srv.duration_minutes,
                srv.price, srv.discount_price, srv.image_url,
                bool(srv.is_active), bool(srv.is_featured), srv.nail_subcategory_id
            ))
            new_id = cursor.lastrowid
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to create service: {str(e)}")

        cursor.execute("""
        SELECT s.*, c.name as category_name, nsc.name as nail_subcategory_name, nsc.slug as nail_subcategory_slug
        FROM services s
        JOIN categories c ON s.category_id = c.id
        LEFT JOIN nail_subcategories nsc ON s.nail_subcategory_id = nsc.id
        WHERE s.id = ?
        """, (new_id,))
        return format_service_row(cursor.fetchone())

@router.put("/{service_id}", response_model=ServiceResponse)
def update_service(service_id: int, srv: ServiceUpdate, current_admin: dict = Depends(get_current_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM services WHERE id = %s", (service_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Service not found")

        updates = []
        params = []
        if srv.category_id is not None:
            updates.append("category_id = %s")
            params.append(srv.category_id)
        if srv.name is not None:
            updates.append("name = %s")
            params.append(srv.name)
            if srv.slug is None:
                updates.append("slug = %s")
                params.append(slugify(srv.name))
        if srv.slug is not None:
            updates.append("slug = %s")
            params.append(slugify(srv.slug))
        if srv.description is not None:
            updates.append("description = %s")
            params.append(srv.description)
        if srv.duration_minutes is not None:
            updates.append("duration_minutes = %s")
            params.append(srv.duration_minutes)
        if srv.price is not None:
            updates.append("price = %s")
            params.append(srv.price)
        if srv.discount_price is not None:
            updates.append("discount_price = %s")
            params.append(srv.discount_price if srv.discount_price > 0 else None)
        if srv.image_url is not None:
            updates.append("image_url = %s")
            params.append(srv.image_url)
        if srv.is_active is not None:
            updates.append("is_active = %s")
            params.append(srv.is_active)
        if srv.is_featured is not None:
            updates.append("is_featured = %s")
            params.append(srv.is_featured)
        if srv.subcategory_id is not None:
            target_category = srv.category_id if srv.category_id is not None else existing["category_id"]
            cursor.execute("SELECT category_id FROM subcategories WHERE id = %s", (srv.subcategory_id,))
            sc = cursor.fetchone()
            if not sc or sc["category_id"] != target_category:
                raise HTTPException(status_code=400, detail="Subcategory does not belong to the selected category")
            updates.append("subcategory_id = %s")
            params.append(srv.subcategory_id)

        if updates:
            params.append(service_id)
            cursor.execute(f"UPDATE services SET {', '.join(updates)} WHERE id = %s", params)

        cursor.execute("""
        SELECT s.*, c.name as category_name, sc.name as subcategory_name, sc.slug as subcategory_slug
        FROM services s
        JOIN categories c ON s.category_id = c.id
        LEFT JOIN subcategories sc ON s.subcategory_id = sc.id
        WHERE s.id = %s
        """, (service_id,))
        return format_service_row(cursor.fetchone())

@router.delete("/{service_id}")
def delete_service(service_id: int, current_admin: dict = Depends(get_current_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM services WHERE id = %s", (service_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Service not found")

        # Safety: bookings reference this service with ON DELETE RESTRICT, so a
        # hard delete would violate the foreign key. Show a clear error instead
        # of hiding it — real client history must never be silently removed.
        cursor.execute(
            "SELECT COUNT(*) as count FROM bookings WHERE service_id = %s",
            (service_id,)
        )
        booking_count = cursor.fetchone()["count"]
        if booking_count and booking_count > 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"This treatment cannot be deleted because it is linked to {booking_count} "
                    f"existing booking{'s' if booking_count != 1 else ''}. "
                    "You can hide it from the menu by toggling it inactive instead."
                )
            )

        # Safe to delete: offers reference services with ON DELETE SET NULL, so
        # they simply lose their service link (no unrelated records are removed).
        try:
            cursor.execute("DELETE FROM services WHERE id = %s", (service_id,))
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Unable to delete this treatment because it is referenced by other records: {e}"
            )
    return {"status": "success", "message": "Service deleted"}
