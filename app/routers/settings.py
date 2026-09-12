from fastapi import APIRouter, HTTPException, Depends
from app.database import get_db
from app.auth import get_current_admin
from app.models import SalonSettingsUpdate, SalonSettingsResponse

router = APIRouter(prefix="/api/settings", tags=["settings"])

@router.get("", response_model=SalonSettingsResponse)
def get_settings():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM salon_settings WHERE id = 1")
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Settings not found")
        return dict(row)

@router.put("", response_model=SalonSettingsResponse)
def update_settings(settings: SalonSettingsUpdate, current_admin: dict = Depends(get_current_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM salon_settings WHERE id = 1")
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Settings not found")

        updates = []
        params = []
        for field, value in settings.model_dump(exclude_unset=True).items():
            if value is not None:
                updates.append(f"{field} = ?")
                params.append(value)

        if updates:
            params.append(1)
            cursor.execute(f"UPDATE salon_settings SET {', '.join(updates)} WHERE id = ?", params)

        cursor.execute("SELECT * FROM salon_settings WHERE id = 1")
        return dict(cursor.fetchone())
