from datetime import date
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from app.database import get_db
from app.auth import get_current_admin
from app.models import OfferCreate, OfferUpdate, OfferResponse

router = APIRouter(prefix="/api/offers", tags=["offers"])

def format_offer_row(row) -> dict:
    d = dict(row)
    orig = d.get("original_price") or 0.0
    disc = d.get("discounted_price") or 0.0
    if orig > 0 and disc < orig:
        d["discount_percent"] = round(((orig - disc) / orig) * 100)
    else:
        d["discount_percent"] = 0
    return d

@router.get("", response_model=List[OfferResponse])
def get_offers(include_inactive: bool = False, featured_only: bool = False):
    today_str = date.today().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        query = """
        SELECT o.*, s.name as service_name
        FROM offers o
        LEFT JOIN services s ON o.service_id = s.id
        WHERE 1=1
        """
        params = []

        if not include_inactive:
            # Public view: must be active and not expired
            query += " AND o.is_active = 1 AND o.start_date <= ? AND o.end_date >= ?"
            params.extend([today_str, today_str])

        if featured_only:
            query += " AND o.is_featured = 1"

        query += " ORDER BY o.is_featured DESC, o.created_at DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [format_offer_row(r) for r in rows]

@router.get("/{offer_id}", response_model=OfferResponse)
def get_offer(offer_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT o.*, s.name as service_name
        FROM offers o
        LEFT JOIN services s ON o.service_id = s.id
        WHERE o.id = ?
        """, (offer_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Offer not found")
        return format_offer_row(row)

@router.post("", response_model=OfferResponse)
def create_offer(off: OfferCreate, current_admin: dict = Depends(get_current_admin)):
    orig = off.original_price
    disc = off.discounted_price
    calc_percent = round(((orig - disc) / orig) * 100) if orig > 0 and disc < orig else 0
    percent = off.discount_percent or calc_percent

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO offers (
            service_id, title, description, original_price, discounted_price,
            discount_percent, start_date, end_date, image_url, is_active, is_featured
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            off.service_id, off.title, off.description, off.original_price, off.discounted_price,
            percent, off.start_date, off.end_date, off.image_url,
            1 if off.is_active else 0,
            1 if off.is_featured else 0
        ))
        new_id = cursor.lastrowid

        cursor.execute("""
        SELECT o.*, s.name as service_name
        FROM offers o
        LEFT JOIN services s ON o.service_id = s.id
        WHERE o.id = ?
        """, (new_id,))
        return format_offer_row(cursor.fetchone())

@router.put("/{offer_id}", response_model=OfferResponse)
def update_offer(offer_id: int, off: OfferUpdate, current_admin: dict = Depends(get_current_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM offers WHERE id = ?", (offer_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Offer not found")

        updates = []
        params = []
        if off.service_id is not None:
            updates.append("service_id = ?")
            params.append(off.service_id if off.service_id > 0 else None)
        if off.title is not None:
            updates.append("title = ?")
            params.append(off.title)
        if off.description is not None:
            updates.append("description = ?")
            params.append(off.description)
        if off.original_price is not None:
            updates.append("original_price = ?")
            params.append(off.original_price)
        if off.discounted_price is not None:
            updates.append("discounted_price = ?")
            params.append(off.discounted_price)
        if off.discount_percent is not None:
            updates.append("discount_percent = ?")
            params.append(off.discount_percent)
        if off.start_date is not None:
            updates.append("start_date = ?")
            params.append(off.start_date)
        if off.end_date is not None:
            updates.append("end_date = ?")
            params.append(off.end_date)
        if off.image_url is not None:
            updates.append("image_url = ?")
            params.append(off.image_url)
        if off.is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if off.is_active else 0)
        if off.is_featured is not None:
            updates.append("is_featured = ?")
            params.append(1 if off.is_featured else 0)

        if updates:
            params.append(offer_id)
            cursor.execute(f"UPDATE offers SET {', '.join(updates)} WHERE id = ?", params)

        cursor.execute("""
        SELECT o.*, s.name as service_name
        FROM offers o
        LEFT JOIN services s ON o.service_id = s.id
        WHERE o.id = ?
        """, (offer_id,))
        return format_offer_row(cursor.fetchone())

@router.delete("/{offer_id}")
def delete_offer(offer_id: int, current_admin: dict = Depends(get_current_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM offers WHERE id = ?", (offer_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Offer not found")
        cursor.execute("DELETE FROM offers WHERE id = ?", (offer_id,))
    return {"status": "success", "message": "Offer deleted"}
