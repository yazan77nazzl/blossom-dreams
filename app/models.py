from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field

# --- Auth Schemas ---
class AdminLoginRequest(BaseModel):
    username: str
    password: str

class AdminUserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AdminUserResponse

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

# --- Category Schemas ---
class CategoryBase(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    display_order: Optional[int] = 0
    icon: Optional[str] = "sparkles"
    is_active: Optional[bool] = True

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    display_order: Optional[int] = None
    icon: Optional[str] = None
    is_active: Optional[bool] = None

class CategoryResponse(CategoryBase):
    id: int

# --- Service Schemas ---
class ServiceBase(BaseModel):
    category_id: int
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: int = 60
    price: float
    discount_price: Optional[float] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = True
    is_featured: Optional[bool] = False

class ServiceCreate(ServiceBase):
    pass

class ServiceUpdate(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    price: Optional[float] = None
    discount_price: Optional[float] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None

class ServiceResponse(ServiceBase):
    id: int
    category_name: Optional[str] = None
    discount_percent: Optional[int] = None

# --- Offer Schemas ---
class OfferBase(BaseModel):
    service_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    original_price: float
    discounted_price: float
    discount_percent: Optional[int] = None
    start_date: str
    end_date: str
    image_url: Optional[str] = None
    is_active: Optional[bool] = True
    is_featured: Optional[bool] = False

class OfferCreate(OfferBase):
    pass

class OfferUpdate(BaseModel):
    service_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    original_price: Optional[float] = None
    discounted_price: Optional[float] = None
    discount_percent: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None

class OfferResponse(OfferBase):
    id: int
    service_name: Optional[str] = None

# --- Booking Schemas ---
class BookingCreate(BaseModel):
    service_id: int
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    notes: Optional[str] = None
    appointment_date: str  # YYYY-MM-DD
    appointment_time: str  # HH:MM (24h)

class BookingStatusUpdate(BaseModel):
    status: str  # pending, confirmed, completed, cancelled, no_show

class BookingResponse(BaseModel):
    id: int
    booking_code: str
    service_id: int
    service_name: Optional[str] = None
    service_duration: Optional[int] = None
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    notes: Optional[str] = None
    appointment_date: str
    appointment_time: str
    duration_minutes: int
    status: str
    price: float
    created_at: str

# --- Availability Schemas ---
class DaySchedule(BaseModel):
    day_of_week: int
    day_name: str
    is_open: bool
    open_time: str
    close_time: str
    slot_interval_minutes: int = 30

class BreakTimeItem(BaseModel):
    id: Optional[int] = None
    day_of_week: int
    label: str = "Break"
    start_time: str
    end_time: str

class ClosedDateItem(BaseModel):
    id: Optional[int] = None
    closed_date: str
    reason: str

class AvailabilityConfigResponse(BaseModel):
    schedule: List[DaySchedule]
    breaks: List[BreakTimeItem]
    closed_dates: List[ClosedDateItem]

# --- Gallery Schemas ---
class GalleryImageCreate(BaseModel):
    title: Optional[str] = None
    caption: Optional[str] = None
    image_url: str
    category: Optional[str] = "All"
    is_featured: Optional[bool] = False
    display_order: Optional[int] = 0

class GalleryImageResponse(GalleryImageCreate):
    id: int
    created_at: str

# --- Salon Settings Schemas ---
class SalonSettingsUpdate(BaseModel):
    salon_name: Optional[str] = None
    tagline: Optional[str] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    whatsapp_number: Optional[str] = None
    instagram_url: Optional[str] = None
    tiktok_url: Optional[str] = None
    address: Optional[str] = None
    google_maps_url: Optional[str] = None
    opening_hours_text: Optional[str] = None
    currency_symbol: Optional[str] = None
    announcement_text: Optional[str] = None

class SalonSettingsResponse(BaseModel):
    id: int
    salon_name: str
    tagline: Optional[str] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    whatsapp_number: Optional[str] = None
    instagram_url: Optional[str] = None
    tiktok_url: Optional[str] = None
    address: Optional[str] = None
    google_maps_url: Optional[str] = None
    opening_hours_text: Optional[str] = None
    currency_symbol: str
    announcement_text: Optional[str] = None
