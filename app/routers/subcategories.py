import re
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from app.database import get_db
from app.auth import get_current_admin
from app.models import SubcategoryCreate, SubcategoryUpdate, SubcategoryResponse

router = APIRouter(prefix="/api/subcategories", tags=["subcategories"])

def slugify(text: str) -> str:
    text = text.lower().strip()
    return re.sub(r'[\s\W-]+', '-', text).strip('-')

@router.get("", response_model=List[SubcategoryResponse])
def list_subcategories(
    category_id: Optional[int] = Query(None),
    include_inactive: bool = False,
    include_service_count: bool = True,
):
    with get_db() as conn:
        cursor = conn.cursor()
        if include_service_count:
            query = """
                SELECT sc.*, c.name as category_name,
                       COALESCE(svc.service_count, 0) as services_count
                FROM subcategories sc
                LEFT JOIN categories c ON sc.category_id = c.id AND sc.organization_id = c.organization_id
                LEFT JOIN (
                    SELECT subcategory_id, COUNT(*) as service_count
                    FROM services
                    WHERE subcategory_id IS NOT NULL
                    GROUP BY subcategory_id
                ) svc ON sc.id = svc.subcategory_id
                WHERE 1=1
            """
        else:
            query = """
                SELECT sc.*, c.name as category_name
                FROM subcategories sc
                LEFT JOIN categories c ON sc.category_id = c.id AND sc.organization_id = c.organization_id
                WHERE 1=1
            """
        params = []
        if category_id is not None:
            query += " AND sc.category_id = %s"
            params.append(category_id)
        if not include_inactive:
            query += " AND sc.is_active = TRUE"
        query += " ORDER BY sc.display_order ASC, sc.name ASC"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

@router.get("/{sub_id}", response_model=SubcategoryResponse)
def get_subcategory(sub_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT sc.*, c.name as category_name,
                   COALESCE(svc.service_count, 0) as services_count
            FROM subcategories sc
            LEFT JOIN categories c ON sc.category_id = c.id AND sc.organization_id = c.organization_id
            LEFT JOIN (
                SELECT subcategory_id, COUNT(*) as service_count
                FROM services
                WHERE subcategory_id IS NOT NULL
                GROUP BY subcategory_id
            ) svc ON sc.id = svc.subcategory_id
            WHERE sc.id = %s
        """, (sub_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Subcategory not found")
        return dict(row)

@router.patch("/{sub_id}", response_model=SubcategoryResponse)
def update_subcategory(sub_id: int, payload: SubcategoryUpdate, current_admin: dict = Depends(get_current_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subcategories WHERE id = %s", (sub_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Subcategory not found")
        updates = []
        params = []
        if payload.name is not None:
            updates.append("name = %s")
            params.append(payload.name)
            if payload.slug is None:
                updates.append("slug = %s")
                params.append(slugify(payload.name))
        if payload.slug is not None:
            updates.append("slug = %s")
            params.append(slugify(payload.slug))
        if payload.description is not None:
            updates.append("description = %s")
            params.append(payload.description)
        if payload.display_order is not None:
            updates.append("display_order = %s")
            params.append(payload.display_order)
        if payload.is_active is not None:
            updates.append("is_active = %s")
            params.append(bool(payload.is_active))
        if updates:
            updates.append("updated_at = now()")
            params.append(sub_id)
            cursor.execute(f"UPDATE subcategories SET {', '.join(updates)} WHERE id = %s", params)
        cursor.execute("""
            SELECT sc.*, c.name as category_name,
                   COALESCE(svc.service_count, 0) as services_count
            FROM subcategories sc
            LEFT JOIN categories c ON sc.category_id = c.id AND sc.organization_id = c.organization_id
            LEFT JOIN (
                SELECT subcategory_id, COUNT(*) as service_count
                FROM services
                WHERE subcategory_id IS NOT NULL
                GROUP BY subcategory_id
            ) svc ON sc.id = svc.subcategory_id
            WHERE sc.id = %s
        """, (sub_id,))
        return dict(cursor.fetchone())

@router.delete("/{sub_id}")
def delete_subcategory(sub_id: int, current_admin: dict = Depends(get_current_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM subcategories WHERE id = %s", (sub_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Subcategory not found")
        cursor.execute("SELECT COUNT(*) as cnt FROM services WHERE subcategory_id = %s", (sub_id,))
        cnt = cursor.fetchone()["cnt"]
        if cnt and cnt > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete '{existing['name']}' because it has {cnt} service(s) assigned. Reassign or delete those services first."
            )
        cursor.execute("DELETE FROM subcategories WHERE id = %s", (sub_id,))
    return {"status": "success", "message": "Subcategory deleted"}

@router.post("", response_model=SubcategoryResponse)
def create_subcategory(payload: SubcategoryCreate, current_admin: dict = Depends(get_current_admin)):
    slug = payload.slug or slugify(payload.name)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM categories WHERE id = %s", (payload.category_id,))
        cat = cursor.fetchone()
        if not cat:
            raise HTTPException(status_code=400, detail="Parent category not found")
        try:
            cursor.execute("""
                INSERT INTO subcategories (organization_id, category_id, name, slug, description, display_order, is_active)
                VALUES (current_setting('app.organization_id')::uuid, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (payload.category_id, payload.name, slug, payload.description, payload.display_order or 0, bool(payload.is_active)))
            new_row = cursor.fetchone()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to create subcategory: {str(e)}")
        cursor.execute("""
            SELECT sc.*, c.name as category_name, 0 as services_count
            FROM subcategories sc
            LEFT JOIN categories c ON sc.category_id = c.id AND sc.organization_id = c.organization_id
            WHERE sc.id = %s
        """, (new_row["id"],))
        return dict(cursor.fetchone())