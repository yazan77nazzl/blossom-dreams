import logging
import os
import uuid
import shutil
from pathlib import Path
import httpx
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.auth import get_current_admin
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/upload", tags=["upload"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "public" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


async def _store_supabase(content: bytes, filename: str, content_type: str = "application/octet-stream") -> str:
    """Upload file bytes to the public Supabase Storage bucket and return its public URL."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(
            status_code=503,
            detail="Supabase storage is not configured (missing SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY).",
        )
    upload_url = f"{settings.SUPABASE_URL}/storage/v1/object/{settings.SUPABASE_STORAGE_BUCKET}/{filename}"
    hostname = settings.SUPABASE_URL.split("//")[-1] if settings.SUPABASE_URL.startswith(("http://", "https://")) else settings.SUPABASE_URL[:40]
    logger.info("Supabase upload URL hostname=%s, bucket=%s", hostname, settings.SUPABASE_STORAGE_BUCKET)
    headers = {
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "x-upsert": "true",
        "Content-Type": content_type,
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            logger.info("FINAL_UPLOAD_URL_REPR=%r", upload_url)
            logger.info("SUPABASE_URL_REPR=%r", settings.SUPABASE_URL)
            logger.info("UPLOAD_BUCKET_REPR=%r", settings.SUPABASE_STORAGE_BUCKET)
            response = await client.post(upload_url, content=content, headers=headers)
    except httpx.HTTPError as exc:
        logger.exception("Supabase storage upload request failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach the image storage service: {exc}",
        ) from exc
    logger.info("Supabase upload response status: %s for %s", response.status_code, filename)
    if response.status_code not in (200, 201):
        error_body = response.text[:500] if response.text else "(empty body)"
        logger.error("Supabase upload failed: HTTP %s, body: %s", response.status_code, error_body)
        raise HTTPException(
            status_code=502,
            detail=f"Image storage failed (HTTP {response.status_code}): {error_body}",
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

    # Production: persist uploads in Supabase. Development can fall back to
    # local storage when Supabase credentials are not configured, which keeps
    # the admin upload workflow usable without hiding a production misconfiguration.
    use_supabase = settings.UPLOAD_STORAGE == "supabase"
    supabase_ready = bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY)
    if use_supabase and supabase_ready:
        url = await _store_supabase(content, unique_filename, content_type=file.content_type or "application/octet-stream")
        return {
            "status": "success",
            "url": url,
            "filename": unique_filename
        }
    if use_supabase and settings.IS_PRODUCTION:
        raise HTTPException(
            status_code=503,
            detail="Supabase storage is not configured (missing SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY).",
        )
    if use_supabase and not supabase_ready:
        print("[Upload] Supabase is not configured; using local development storage.")

    # Local development: save to the project filesystem (not persistent on hosted free tier).
    dest_path = UPLOAD_DIR / unique_filename

    with open(dest_path, "wb") as f:
        f.write(content)

    return {
        "status": "success",
        "url": f"/static/uploads/{unique_filename}",
        "filename": unique_filename
    }
