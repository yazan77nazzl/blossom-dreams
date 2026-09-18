import re
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from app.database import get_db
from app.auth import get_current_admin
from app.models import NailSubcategoryCreate, NailSubcategoryUpdate, NailSubcategoryResponse

router = APIRouter(prefix="/api/nail-subcategories", tags=["nail-subcategories"])

def slugify(text: str) -> str:
    text = text.lower().strip()
    return re.sub(r'[\s\W-]+', '-', text).strip('-')

@router.get("", response_model=List[NailSubcategoryResponse])
def get_nail_subcategories(
    include_inactive: bool = False,
    include_service_count: bool = True
):
    with get_db() as conn:
        cursor = conn.cursor()
        
        if include_service_count:
            query = """
                SELECT nsc.*, COALESCE(svc.service_count, 0) as services_count
                FROM nail_subcategories nsc
                LEFT JOIN (
                    SELECT nail_subcategory_id, COUNT(*) as service_count
                    FROM services
                    WHERE nail_subcategory_id IS NOT NULL
                    GROUP BY nail_subcategory_id
                ) svc ON nsc.id = svc.nail_subcategory_id
                WHERE 1=1
            """
        else:
            query = "SELECT * FROM nail_subcategories WHERE 1=1"
        
        if not include_inactive:
            query += " AND nsc.is_active = TRUE"
        
        query += " ORDER BY nsc.display_order ASC, nsc.name ASC"
        
        cursor.execute(query)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

@router.get("/{subcat_id}", response_model=NailSubcategoryResponse)
def get_nail_subcategory(subcat_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT nsc.*, COALESCE(svc.service_count, 0) as services_count
            FROM nail_subcategories nsc
            LEFT JOIN (
                SELECT nail_subcategory_id, COUNT(*) as service_count
                FROM services
                WHERE nail_subcategory_id IS NOT NULL
                GROUP BY nail_subcategory_id
            ) svc ON nsc.id = svc.nail_subcategory_id
            WHERE nsc.id = ?
        """, (subcat_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Nail subcategory not found")
        return dict(row)

@router.post("", response_model=NailSubcategoryResponse)
def create_nail_subcategory(nsc: NailSubcategoryCreate, current_admin: dict = Depends(get_current_admin)):
    slug = nsc.slug or slugify(nsc.name)
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO nail_subcategories (name, slug, display_order, is_active)
                VALUES (?, ?, ?, ?)
            """, (nsc.name, slug, nsc.display_order or 0, bool(nsc.is_active)))
            new_id = cursor.lastrowid
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to create nail subcategory: {str(e)}")

        cursor.execute("""
            SELECT nsc.*, COALESCE(svc.service_count, 0) as services_count
            FROM nail_subcategories nsc
            LEFT JOIN (
                SELECT nail_subcategory_id, COUNT(*) as service_count
                FROM services
                WHERE nail_subcategory_id IS NOT NULL
                GROUP BY nail_subcategory_id
            ) svc ON nsc.id = svc.nail_subcategory_id
            WHERE nsc.id = ?
        """, (new_id,))
        return dict(cursor.fetchone())

@router.patch("/{subcat_id}", response_model=NailSubcategoryResponse)
def update_nail_subcategory(subcat_id: int, nsc: NailSubcategoryUpdate, current_admin: dict = Depends(get_current_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM nail_subcategories WHERE id = ?", (subcat_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Nail subcategory not found")

        updates = []
        params = []
        if nsc.name is not None:
            updates.append("name = ?")
            params.append(nsc.name)
            if not nsc.slug:
                updates.append("slug = ?")
                params.append(slugify(nsc.name))
        if nsc.slug is not None:
            updates.append("slug = ?")
            params.append(slugify(nsc.slug))
        if nsc.display_order is not None:
            updates.append("display_order = ?")
            params.append(nsc.display_order)
        if nsc.is_active is not None:
            updates.append("is_active = ?")
            params.append(nsc.is_active)

        if updates:
            updates.append("updated_at = now()")
            params.append(subcat_id)
            cursor.execute(f"UPDATE nail_subcategories SET {', '.join(updates)} WHERE id = ?", params)

        cursor.execute("""
            SELECT nsc.*, COALESCE(svc.service_count, 0) as services_count
            FROM nail_subcategories nsc
            LEFT JOIN (
                SELECT nail_subcategory_id, COUNT(*) as service_count
                FROM services
                WHERE nail_subcategory_id IS NOT NULL
                GROUP BY nail_subcategory_id
            ) svc ON nsc.id = svc.nail_subcategory_id
            WHERE nsc.id = ?
        """, (subcat_id,))
        return dict(cursor.fetchone())

@router.delete("/{subcat_id}")
def delete_nail_subcategory(subcat_id: int, current_admin: dict = Depends(get_current_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM nail_subcategories WHERE id = ?", (subcat_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Nail subcategory not found")

        # Check if any services are assigned to this subcategory
        cursor.execute("SELECT COUNT(*) as count FROM services WHERE nail_subcategory_id = ?", (subcat_id,))
        service_count = cursor.fetchone()["count"]
        if service_count and service_count > 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Cannot delete '{existing['name']}' because it has {service_count} "
                    f"service{'s' if service_count != 1 else ''} assigned. "
                    "Please reassign or delete those services first."
                )
            )

        cursor.execute("DELETE FROM nail_subcategories WHERE id = ?", (subcat_id,))
    return {"status": "success", "message": "Nail subcategory deleted"}