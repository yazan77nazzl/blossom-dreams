from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from app.database import get_db
from app.auth import get_current_admin
from app.models import GalleryImageCreate, GalleryImageResponse

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
            query += " AND is_featured = 1"

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
            1 if item.is_featured else 0,
            item.display_order or 0
        ))
        new_id = cursor.lastrowid
        cursor.execute("SELECT * FROM gallery_images WHERE id = ?", (new_id,))
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
