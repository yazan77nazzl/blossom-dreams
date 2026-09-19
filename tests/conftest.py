import os
import pathlib
import tempfile

# Set a test environment before any app modules are imported
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["ADMIN_PASSWORD"] = "TestAdminPass123!"

# Use an isolated temporary SQLite database for the whole test session
_TEST_DB = pathlib.Path(tempfile.gettempdir()) / "blossom_dreams_test.db"
for _ext in ("", "-wal", "-shm"):
    _p = pathlib.Path(str(_TEST_DB) + _ext)
    if _p.exists():
        _p.unlink()
os.environ["DATABASE_URL"] = "sqlite:///" + _TEST_DB.as_posix()

# Now safe to import app modules
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db
from app.seed_data import seed_database

# Initialise DB once per session
@pytest.fixture(scope="session", autouse=True)
def _init_db():
    init_db()
    seed_database()
    yield

@pytest.fixture(scope="function")
def client():
    return TestClient(app)