import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env so DATABASE_URL / SECRET_KEY etc. work locally too
load_dotenv(BASE_DIR / ".env")


class Settings:
    def __init__(self):
        self.ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "development").lower()
        self.IS_PRODUCTION: bool = self.ENVIRONMENT == "production"

        # Database URL (supports postgresql:// or sqlite:///...)
        default_sqlite_path = BASE_DIR / "blossom_dreams.db"
        self.DATABASE_URL: str = os.environ.get("DATABASE_URL", "")
        if self.IS_PRODUCTION and not self.DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL is required in production. Create a free Neon "
                "Postgres database and set DATABASE_URL to its connection string "
                "(postgresql://...?sslmode=require). See README 'Deployment'."
            )
        if not self.DATABASE_URL:
            self.DATABASE_URL = f"sqlite:///{default_sqlite_path.as_posix()}"
        # Fix Render/Heroku postgres:// schema prefix to postgresql://
        if self.DATABASE_URL.startswith("postgres://"):
            self.DATABASE_URL = self.DATABASE_URL.replace("postgres://", "postgresql://", 1)

        # JWT Secret Key — must be explicitly set in production, otherwise admin
        # tokens would rotate on every restart.
        secret = os.environ.get("SECRET_KEY") or os.environ.get("BLOSSOM_SECRET_KEY")
        if not secret and self.IS_PRODUCTION:
            raise RuntimeError(
                "SECRET_KEY is required in production. Generate one with:\n"
                '  python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        self.SECRET_KEY: str = secret or "blossom_dreams_lb_luxury_super_secret_key_2025"
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

        # Upload storage backend: "local" (default, dev/ephemeral) or "supabase"
        # (production — persistent free object storage for salon images).
        self.UPLOAD_STORAGE: str = os.environ.get("UPLOAD_STORAGE", "local").lower()
        self.SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "").rstrip("/")
        self.SUPABASE_SERVICE_ROLE_KEY: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        self.SUPABASE_STORAGE_BUCKET: str = os.environ.get("SUPABASE_STORAGE_BUCKET", "uploads")

        # Default Admin Credentials for initial seeding
        self.ADMIN_USERNAME: str = os.environ.get("ADMIN_USERNAME", "admin")
        self.ADMIN_EMAIL: str = os.environ.get("ADMIN_EMAIL", "admin@blossomdreams.com")
        self.ADMIN_PASSWORD: str = os.environ.get("ADMIN_PASSWORD", "BlossomAdmin2025!")
        self.ADMIN_FULL_NAME: str = os.environ.get("ADMIN_FULL_NAME", "Blossom Admin")


settings = Settings()
