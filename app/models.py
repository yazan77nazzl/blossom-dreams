from typing import Optional, List, Literal
from pydantic import BaseModel, EmailStr, Field

# --- Auth Schemas ---
class AdminLoginRequest(BaseModel):
    username: str
    password: str

class AdminUserResponse(BaseModel):
    id: str
    organization_id: str
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

# --- Subcategory Schemas (generic, belongs to a Main Category) ---
class SubcategoryBase(BaseModel):
    category_id: int                     # required – parent Main Category
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    display_order: Optional[int] = 0
    is_active: Optional[bool] = True

class SubcategoryCreate(SubcategoryBase):
    pass

class SubcategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None

class SubcategoryResponse(SubcategoryBase):
    id: int
    category_name: Optional[str] = None   # joined for UI convenience
    services_count: Optional[int] = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

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
    subcategory_id: Optional[int] = None

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
    subcategory_id: Optional[int] = None

class ServiceResponse(ServiceBase):
    id: int
    category_name: Optional[str] = None
    subcategory_name: Optional[str] = None
    subcategory_slug: Optional[str] = None
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
    service_ids: List[int] = Field(default_factory=list, description="List of service IDs")
    offer_ids: List[int] = Field(default_factory=list, description="List of offer IDs")
    # Backward compatibility single service_id (optional)
    service_id: Optional[int] = None
    location_id: Optional[int] = None
    customer_name: str = Field(..., min_length=2, max_length=120, description="Full name of the client")
    customer_phone: str = Field(..., min_length=5, max_length=30, description="Phone / WhatsApp number")
    customer_email: Optional[str] = Field(
        None,
        max_length=120,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        description="Optional email address",
    )
    notes: Optional[str] = Field(None, max_length=1000)
    appointment_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD")
    appointment_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="HH:MM (24h)")

class BookingStatusUpdate(BaseModel):
    status: Literal["pending", "confirmed", "completed", "cancelled", "no_show"]

class BookingResponse(BaseModel):
    id: int
    booking_code: str
    service_id: int
    service_name: Optional[str] = None
    service_duration: Optional[int] = None
    location_id: Optional[int] = None
    location_name: Optional[str] = None
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

# --- Location Schemas ---
class LocationBase(BaseModel):
    slug: str = Field(..., max_length=60, description="Unique URL-friendly identifier")
    name: str = Field(..., min_length=2, max_length=120)
    address: Optional[str] = Field(None, max_length=200)
    google_maps_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    display_order: Optional[int] = 0
    is_active: Optional[bool] = True

class LocationCreate(LocationBase):
    pass

class LocationUpdate(BaseModel):
    slug: Optional[str] = None
    name: Optional[str] = None
    address: Optional[str] = None
    google_maps_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None

class LocationResponse(LocationBase):
    id: int

# --- Availability Schemas ---
class DaySchedule(BaseModel):
    day_of_week: int
    day_name: str
    is_open: bool
    open_time: str
    close_time: str
    slot_interval_minutes: int = 30
    buffer_minutes: int = 0

class ClosedDateItem(BaseModel):
    id: Optional[int] = None
    closed_date: str
    reason: str

class AvailabilityConfigResponse(BaseModel):
    schedule: List[DaySchedule]
    closed_dates: List[ClosedDateItem]
    locations: List[LocationResponse] = []

class AvailabilityConfigUpdate(BaseModel):
    buffer_minutes: int = 0

# --- Gallery Schemas ---
class GalleryImageCreate(BaseModel):
    title: Optional[str] = None
    caption: Optional[str] = None
    image_url: str
    category: Optional[str] = "All"
    is_featured: Optional[bool] = False
    display_order: Optional[int] = 0

class GalleryImageUpdate(BaseModel):
    title: Optional[str] = None
    caption: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    is_featured: Optional[bool] = None
    display_order: Optional[int] = None

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
    currency_symbol: Optional[str] = None
    announcement_text: Optional[str] = None
