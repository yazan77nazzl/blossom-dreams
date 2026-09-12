import os
import uuid
import shutil
from pathlib import Path
import httpx
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.auth import get_current_admin
from app.config import settings

router = APIRouter(prefix="/api/upload", tags=["upload"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "public" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


async def _store_supabase(content: bytes, filename: str) -> str:
    """Upload file bytes to the public Supabase Storage bucket and return its public URL."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(
            status_code=503,
            detail="Supabase storage is not configured (missing SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY).",
        )
    upload_url = f"{settings.SUPABASE_URL}/storage/v1/object/{settings.SUPABASE_STORAGE_BUCKET}/{filename}"
    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "x-upsert": "true",
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(upload_url, content=content, headers=headers)
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Could not reach the image storage service.")
    if response.status_code not in (200, 201):
        raise HTTPException(
            status_code=502,
            detail=f"Image storage failed (HTTP {response.status_code}).",
        )
    return f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.SUPABASE_STORAGE_BUCKET}/{filename}"


@router.post("")
async def upload_image(file: UploadFile = File(...), current_admin: dict = Depends(get_current_admin)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{ext}'. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Read content to verify size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (maximum 10MB).")

    unique_filename = f"{uuid.uuid4().hex[:12]}_{Path(file.filename).stem[:20]}{ext}"

    # Production: persist uploads in free Supabase object storage (survives
    # Render's ephemeral disk, restarts, and redeploys).
    if settings.UPLOAD_STORAGE == "supabase":
        url = await _store_supabase(content, unique_filename)
        return {
            "status": "success",
            "url": url,
            "filename": unique_filename
        }

    # Local development: save to the project filesystem (not persistent on hosted free tier).
    dest_path = UPLOAD_DIR / unique_filename

    with open(dest_path, "wb") as f:
        f.write(content)

    return {
        "status": "success",
        "url": f"/static/uploads/{unique_filename}",
        "filename": unique_filename
    }
