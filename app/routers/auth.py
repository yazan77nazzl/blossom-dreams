import logging
from fastapi import APIRouter, HTTPException, Depends, status, Request
from app.database import get_db
from app.auth import verify_password, get_password_hash, create_access_token, get_current_admin
from app.models import AdminLoginRequest, TokenResponse, AdminUserResponse, ChangePasswordRequest
from app.main import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, form_data: AdminLoginRequest):
    logger.info("Login attempt for username: %s", form_data.username)
    print(f"[AUTH DEBUG] Login attempt for username: {form_data.username}", flush=True)
    with get_db() as conn:
        cursor = conn.cursor()
        sql = "SELECT id, organization_id, username, email, hashed_password, full_name, role FROM admin_users WHERE username ILIKE ? OR email ILIKE ?"
        logger.info("Executing login query: %s with params (%s, %s)", sql, form_data.username, form_data.username)
        print(f"[AUTH DEBUG] Executing login query: {sql} with params ({form_data.username}, {form_data.username})", flush=True)
        cursor.execute(sql, (form_data.username, form_data.username))
        user = cursor.fetchone()
        if user:
            logger.info("Query returned user id=%s org_id=%s username=%s email=%s", user["id"], user["organization_id"], user["username"], user["email"])
            print(f"[AUTH DEBUG] Query returned user id={user['id']} org_id={user['organization_id']} username={user['username']} email={user['email']}", flush=True)
        else:
            logger.info("Query returned no rows")
            print("[AUTH DEBUG] Query returned no rows", flush=True)

    if user:
        logger.info("User found: username=%s email=%s", user["username"], user["email"])
        print(f"[AUTH DEBUG] User found: username={user['username']} email={user['email']}", flush=True)
        password_verified = verify_password(form_data.password, user["hashed_password"])
        logger.info("Password verified: %s", password_verified)
        print(f"[AUTH DEBUG] Password verified: {password_verified}", flush=True)
    else:
        logger.info("User not found")
        print("[AUTH DEBUG] User not found", flush=True)
        password_verified = False

    if not user or not password_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user["username"], "user_id": str(user["id"]), "organization_id": str(user["organization_id"])})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user["id"]),
            "organization_id": str(user["organization_id"]),
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"]
        }
    }

@router.get("/me", response_model=AdminUserResponse)
def get_me(current_admin: dict = Depends(get_current_admin)):
    return current_admin

@router.post("/change-password")
def change_password(data: ChangePasswordRequest, current_admin: dict = Depends(get_current_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT hashed_password FROM admin_users WHERE id = ?", (current_admin["id"],))
        row = cursor.fetchone()
        if not row or not verify_password(data.old_password, row["hashed_password"]):
            raise HTTPException(status_code=400, detail="Current password does not match.")

        new_hash = get_password_hash(data.new_password)
        cursor.execute("UPDATE admin_users SET hashed_password = ? WHERE id = ?", (new_hash, current_admin["id"]))

    return {"status": "success", "message": "Password changed successfully."}