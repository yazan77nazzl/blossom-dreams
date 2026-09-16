import logging
import os
import re
from pathlib import Path
from typing import List
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env so DATABASE_URL / SECRET_KEY etc. work locally too
load_dotenv(BASE_DIR / ".env")


class Settings:
    def __init__(self):
        self.ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "development").lower()
        self.IS_PRODUCTION: bool = self.ENVIRONMENT == "production"

        # PostgreSQL/Supabase is the application's only database.  Deliberately
        # fail fast instead of ever creating or falling back to a local SQLite DB.
        self.DATABASE_URL: str = os.environ.get("DATABASE_URL", "").strip()
        if not self.DATABASE_URL:
            raise RuntimeError("DATABASE_URL is required and must point to PostgreSQL.")
        # Fix Render/Heroku postgres:// schema prefix to postgresql://
        if self.DATABASE_URL.startswith("postgres://"):
            self.DATABASE_URL = self.DATABASE_URL.replace("postgres://", "postgresql://", 1)
        if not self.DATABASE_URL.startswith(("postgresql://", "postgresql+psycopg://")):
            raise RuntimeError("DATABASE_URL must be a PostgreSQL connection URL.")
        # `pgbouncer=true` is a Supabase connection hint, not a psycopg/libpq
        # parameter. Keep the pooler host/port and remove only that hint.
        self.DATABASE_URL = re.sub(r"([?&])pgbouncer=true&?", r"\1", self.DATABASE_URL).rstrip("?&")

        # JWT Secret Key — must be explicitly set in production, otherwise admin
        # tokens would rotate on every restart.
        secret = os.environ.get("SECRET_KEY") or os.environ.get("BLOSSOM_SECRET_KEY")
        if not secret:
            raise RuntimeError("SECRET_KEY is required.")
        self.SECRET_KEY: str = secret
        self.ALGORITHM: str = "HS256"
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

        # CORS Origins (comma-separated or '*' for public access)
        cors_raw = os.environ.get("CORS_ORIGINS", "*")
        if cors_raw.strip() == "*":
            self.CORS_ORIGINS: List[str] = ["*"]
        else:
            self.CORS_ORIGINS: List[str] = [origin.strip() for origin in cors_raw.split(",") if origin.strip()]
        # Browsers reject allow_credentials=True together with origin "*".
        self.CORS_ALLOW_CREDENTIALS: bool = "*" not in self.CORS_ORIGINS

        # Public base URL (e.g. https://blossom-dreams-lb.onrender.com)
        self.PUBLIC_BASE_URL: str = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")

        # Salon wall-clock timezone. Availability, "can I book today" and the
        # admin dashboard are computed against the salon's local day, so a UTC
        # container on Render does not shift the "today" boundary for Beirut.
        self.SALON_TIMEZONE: str = os.environ.get("SALON_TIMEZONE", "Asia/Beirut")

        # Upload storage backend: "local" (default, dev/ephemeral) or "supabase"
        # (production — persistent free object storage for salon images).
        self.UPLOAD_STORAGE: str = os.environ.get("UPLOAD_STORAGE", "local").strip().lower()
        self.SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
        self.SUPABASE_SERVICE_ROLE_KEY: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        self.SUPABASE_STORAGE_BUCKET: str = os.environ.get("SUPABASE_STORAGE_BUCKET", "uploads").strip()

        if self.SUPABASE_URL:
            has_protocol = self.SUPABASE_URL.startswith("http://") or self.SUPABASE_URL.startswith("https://")
            hostname = self.SUPABASE_URL.split("//")[-1] if has_protocol else self.SUPABASE_URL[:40]
            logger.info("SUPABASE_URL parsed: protocol=%s, hostname=%s, bucket=%s",
                        "yes" if has_protocol else "NO",
                        hostname,
                        self.SUPABASE_STORAGE_BUCKET)
            if not has_protocol:
                logger.warning("SUPABASE_URL is missing http/https protocol!")
        else:
            logger.warning("SUPABASE_URL is not set")

        # Validate Supabase configuration if UPLOAD_STORAGE is set to "supabase"
        if self.UPLOAD_STORAGE == "supabase":
            if not self.SUPABASE_URL:
                raise RuntimeError(
                    "SUPABASE_URL is required when UPLOAD_STORAGE=supabase. "
                    "Set it to your Supabase project URL (e.g., https://<project-ref>.supabase.co)."
                )
            if not self.SUPABASE_SERVICE_ROLE_KEY:
                raise RuntimeError(
                    "SUPABASE_SERVICE_ROLE_KEY is required when UPLOAD_STORAGE=supabase. "
                    "Get it from Supabase Dashboard → Settings → API → service_role key."
                )
            if not self.SUPABASE_STORAGE_BUCKET:
                raise RuntimeError(
                    "SUPABASE_STORAGE_BUCKET is required when UPLOAD_STORAGE=supabase. "
                    "Set it to your storage bucket name (default: 'uploads')."
                )

        # Default Admin Credentials for initial seeding
        self.ADMIN_USERNAME: str = os.environ.get("ADMIN_USERNAME", "admin")
        self.ADMIN_EMAIL: str = os.environ.get("ADMIN_EMAIL", "admin@blossomdreams.com")
        self.ADMIN_PASSWORD: str = os.environ.get("ADMIN_PASSWORD", "")
        if not self.ADMIN_PASSWORD:
            raise RuntimeError("ADMIN_PASSWORD is required for initial database seeding.")
        self.ADMIN_FULL_NAME: str = os.environ.get("ADMIN_FULL_NAME", "Blossom Admin")


settings = Settings()
