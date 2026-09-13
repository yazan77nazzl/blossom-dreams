from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from app.database import get_db
from app.auth import get_current_admin
from app.models import GalleryImageCreate, GalleryImageResponse
from app.models import GalleryImageUpdate

router = APIRouter(prefix="/api/gallery", tags=["gallery"])

@router.get("", response_model=List[GalleryImageResponse])
def get_gallery_images(category: Optional[str] = None, featured_only: bool = False):
    with get_db() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM gallery_images WHERE 1=1"
        params = []

        if category and category.lower() != "all":
            query += " AND category = ?"
            params.append(category)

        if featured_only:
            query += " AND is_featured = TRUE"

        query += " ORDER BY display_order ASC, created_at DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

@router.post("", response_model=GalleryImageResponse)
def add_gallery_image(item: GalleryImageCreate, current_admin: dict = Depends(get_current_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO gallery_images (title, caption, image_url, category, is_featured, display_order)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            item.title, item.caption, item.image_url,
            item.category or "All",
            bool(item.is_featured),
            item.display_order or 0
        ))
        new_id = cursor.lastrowid
        cursor.execute("SELECT * FROM gallery_images WHERE id = ?", (new_id,))
        return dict(cursor.fetchone())

@router.put("/{image_id}", response_model=GalleryImageResponse)
def update_gallery_image(image_id: int, item: GalleryImageUpdate, current_admin: dict = Depends(get_current_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM gallery_images WHERE id = ?", (image_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Image not found")

        updates = []
        params = []
        for field in ("title", "caption", "image_url", "category", "is_featured", "display_order"):
            value = getattr(item, field)
            if value is not None:
                updates.append(f"{field} = ?")
                params.append(bool(value) if field == "is_featured" else value)

        if updates:
            params.append(image_id)
            cursor.execute(f"UPDATE gallery_images SET {', '.join(updates)} WHERE id = ?", params)

        cursor.execute("SELECT * FROM gallery_images WHERE id = ?", (image_id,))
        return dict(cursor.fetchone())

@router.delete("/{image_id}")
def delete_gallery_image(image_id: int, current_admin: dict = Depends(get_current_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM gallery_images WHERE id = ?", (image_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Image not found")
        cursor.execute("DELETE FROM gallery_images WHERE id = ?", (image_id,))
    return {"status": "success", "message": "Image removed from gallery"}
