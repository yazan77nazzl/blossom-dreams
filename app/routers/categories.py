import re
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from app.database import get_db
from app.auth import get_current_admin
from app.models import CategoryCreate, CategoryUpdate, CategoryResponse

router = APIRouter(prefix="/api/categories", tags=["categories"])

def slugify(text: str) -> str:
    text = text.lower().strip()
    return re.sub(r'[\s\W-]+', '-', text).strip('-')

@router.get("", response_model=List[CategoryResponse])
def get_categories(include_inactive: bool = False):
    with get_db() as conn:
        cursor = conn.cursor()
        if include_inactive:
            cursor.execute("SELECT * FROM categories ORDER BY display_order ASC, name ASC")
        else:
            cursor.execute("SELECT * FROM categories WHERE is_active = 1 ORDER BY display_order ASC, name ASC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

@router.post("", response_model=CategoryResponse)
def create_category(cat: CategoryCreate, current_admin: dict = Depends(get_current_admin)):
    slug = cat.slug or slugify(cat.name)
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
            INSERT INTO categories (name, slug, description, display_order, icon, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (cat.name, slug, cat.description, cat.display_order or 0, cat.icon or 'sparkles', 1 if cat.is_active else 0))
            new_id = cursor.lastrowid
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to create category: {str(e)}")

        cursor.execute("SELECT * FROM categories WHERE id = ?", (new_id,))
        return dict(cursor.fetchone())

@router.put("/{cat_id}", response_model=CategoryResponse)
def update_category(cat_id: int, cat: CategoryUpdate, current_admin: dict = Depends(get_current_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories WHERE id = ?", (cat_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Category not found")

        updates = []
        params = []
        if cat.name is not None:
            updates.append("name = ?")
            params.append(cat.name)
            if not cat.slug:
                updates.append("slug = ?")
                params.append(slugify(cat.name))
        if cat.slug is not None:
            updates.append("slug = ?")
            params.append(slugify(cat.slug))
        if cat.description is not None:
            updates.append("description = ?")
            params.append(cat.description)
        if cat.display_order is not None:
            updates.append("display_order = ?")
            params.append(cat.display_order)
        if cat.icon is not None:
            updates.append("icon = ?")
            params.append(cat.icon)
        if cat.is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if cat.is_active else 0)

        if updates:
            params.append(cat_id)
            cursor.execute(f"UPDATE categories SET {', '.join(updates)} WHERE id = ?", params)

        cursor.execute("SELECT * FROM categories WHERE id = ?", (cat_id,))
        return dict(cursor.fetchone())

@router.delete("/{cat_id}")
def delete_category(cat_id: int, current_admin: dict = Depends(get_current_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM categories WHERE id = ?", (cat_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Category not found")
        
        cursor.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
    return {"status": "success", "message": "Category deleted"}
