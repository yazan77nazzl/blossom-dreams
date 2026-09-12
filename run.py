import sys
import os
import uvicorn
from app.config import settings
from app.database import init_db
from app.seed_data import seed_database


def main():
    # Ensure the banner renders on Windows consoles that default to cp1252
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if not settings.IS_PRODUCTION:
        print("=" * 60)
        print("🌸 BLOSSOM DREAMS - LUXURY SALON PLATFORM")
        print("=" * 60)

    # 1. Initialize Database & Schema
    print("[1/3] Initializing database schema...")
    init_db()

    # 2. Populate Seed Data if fresh
    print("[2/3] Checking & applying initial realistic seed data...")
    seed_database()

    if not settings.IS_PRODUCTION:
        print("[3/3] Starting web server...")
        print("-" * 60)
        print("✨ Public Salon Website: http://127.0.0.1:8000/")
        print("👑 Salon Admin Dashboard: http://127.0.0.1:8000/admin")
        print("📋 API Documentation:    http://127.0.0.1:8000/docs")
        print("-" * 60)
        print("Default Admin Credentials:")
        print("  Username: admin  (or admin@blossomdreams.com)")
        print("  Password: BlossomAdmin2025!")
        print("=" * 60)
    else:
        base_url = settings.PUBLIC_BASE_URL or "your-public-url"
        print(f"[3/3] Starting production server -> {base_url}")

    # Production hardening: reload is a development feature only.
    reload_enabled = os.environ.get("RELOAD", "false").lower() in ("1", "true", "yes")
    if settings.IS_PRODUCTION and reload_enabled:
        print("[WARN] RELOAD is disabled in production; ignoring reload=true.")
        reload_enabled = False

    host = os.environ.get("HOST", "0.0.0.0" if settings.IS_PRODUCTION else "127.0.0.1")
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host=host, port=port, reload=reload_enabled)


if __name__ == "__main__":
    main()