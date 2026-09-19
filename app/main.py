import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import init_db
from app.seed_data import seed_database
from app.routers import auth, services, categories, offers, bookings, availability, gallery, settings as salon_settings_router, upload, locations, subcategories
from app.routers.bookings import admin_router
from app.startup_migration import run_startup_migration

logging.basicConfig(level=logging.INFO)

# Rate limiter (exported for routers)
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per minute"])

BASE_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = BASE_DIR / "public"
UPLOADS_DIR = PUBLIC_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Server] Initializing database...")
    init_db()
    print("[Server] Running startup migration for subcategories...")
    run_startup_migration()
    print("[Server] Checking seed data...")
    seed_database()
    # Diagnostic: confirm admin password is configured (do not log the password itself)
    logger = logging.getLogger(__name__)
    logger.info("Admin password configured: %s (length=%d)", True, len(settings.ADMIN_PASSWORD))
    print(f"[Server] Blossom Dreams is ready in {settings.ENVIRONMENT.upper()} mode!")
    yield

app = FastAPI(
    title="Blossom Dreams API",
    description="Luxury Beauty Salon Booking & Management Platform for Blossom Dreams",
    version="1.0.0",
    lifespan=lifespan,
    debug=not settings.IS_PRODUCTION,
)

# Attach limiter to app state for use in routers
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Production Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    # Content Security Policy – adjust as needed for your assets
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.tailwindcss.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'self'; "
        "form-action 'self'"
    )
    # Enforce HTTPS in production via HSTS
    if settings.IS_PRODUCTION:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    return response

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router)
app.include_router(services.router)
app.include_router(categories.router)
app.include_router(offers.router)
app.include_router(bookings.router)
app.include_router(availability.router)
app.include_router(locations.router)
app.include_router(gallery.router)
app.include_router(salon_settings_router.router)
app.include_router(upload.router)
app.include_router(subcategories.router)
app.include_router(admin_router)

# Mount Static Files (/static points to public directory)
app.mount("/static", StaticFiles(directory=str(PUBLIC_DIR)), name="static")

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "app": "Blossom Dreams",
        "version": "1.0.0",
        "database": "postgresql"
    }

# HTML Entry Points
@app.get("/")
def serve_index():
    index_path = PUBLIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Blossom Dreams Frontend is initializing."}

@app.get("/manifest.json")
def serve_manifest():
    manifest_path = PUBLIC_DIR / "manifest.json"
    if manifest_path.exists():
        return FileResponse(
            manifest_path,
            media_type="application/manifest+json",
            headers={"Cache-Control": "public, max-age=0, must-revalidate"},
        )
    return JSONResponse({"error": "Manifest missing"}, status_code=404)

@app.get("/sw.js")
def serve_service_worker():
    sw_path = PUBLIC_DIR / "sw.js"
    if sw_path.exists():
        return FileResponse(
            sw_path,
            media_type="application/javascript",
            headers={"Cache-Control": "no-cache"},
        )
    return JSONResponse({"error": "Service worker missing"}, status_code=404)

@app.get("/admin")
@app.get("/admin/")
def serve_admin():
    admin_path = PUBLIC_DIR / "admin" / "index.html"
    if admin_path.exists():
        return FileResponse(admin_path)
    return {"message": "Blossom Dreams Admin is initializing."}
