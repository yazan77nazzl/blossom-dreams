# 🌸 Blossom Dreams — Luxury Beauty Salon Platform

A complete, production-quality, mobile-first full-stack web application with automated appointment booking, real-time availability checking, and full salon owner management dashboard built for **Blossom Dreams** in Beirut, Lebanon ([@blossomdreams.lb](https://www.instagram.com/blossomdreams.lb/)).

---

## 💎 Features

### 1. Public Client Experience (`/`)
- **Romantic Luxury Brand Identity**: Inspired by Blossom Dreams' Instagram aesthetic with soft rose blush `#FFF5F7`, vibrant fuchsia `#C026D3`, gold accents `#D4AF37`, Playfair Display serif typography, and delicate floral motifs.
- **Mobile-First Responsive Design**: Optimized for Instagram profile visits on smartphones with touch-friendly navigation, zero horizontal scroll, and floating contact actions.
- **Dynamic Services Menu**: Categorized under *Nails, Lashes, Brows, Skin & Facial, Laser Hair Removal, Glam & Makeup, and Piercing & Tattoo*, with real-time live search.
- **Special Offers & Packages**: Displays promotional bundles with crossed-out original prices, prominent discount badges, and automatic expiration handling.
- **Interactive 4-Step Booking Wizard**:
  1. Service selection with duration and price breakdown
  2. Live date picker with interactive 14-day strip and real-time open slot computation
  3. Client contact form with phone and special requests
  4. Instant booking confirmation receipt with unique reference code (`#BD-XXXXX`)
- **Direct WhatsApp Confirmation**: One-click button generating pre-filled WhatsApp confirmation messages to the salon's official number.
- **Booking Code Verification**: Clients can enter their booking code anytime to check appointment status.
- **Visual Atelier Gallery**: Filterable photo showcase with high-res lightbox previews.
- **Instagram Showcase**: Direct showcase and link to [@blossomdreams.lb](https://www.instagram.com/blossomdreams.lb/).

### 2. Salon Owner Admin Dashboard (`/admin`)
- **Secure Authentication**: Protected routes with bcrypt password hashing and JWT sessions.
- **Overview KPIs**: Today's appointments, upcoming bookings, pending bookings, active services count, and revenue metrics.
- **Bookings Management**:
  - Filter by date, status, service, or customer name/phone.
  - Table view and interactive monthly Calendar view.
  - One-click status management (`Pending`, `Confirmed`, `Completed`, `Cancelled`, `No Show`).
  - Detailed client view with direct WhatsApp chat link.
  - Manual Phone/Walk-in booking creation.
- **Services CRUD**: Add, edit, delete, toggle visibility, and upload images.
- **Special Offers CRUD**: Add, edit, and deactivate promotions with auto-calculated discount percentages.
- **Working Hours & Availability Engine**:
  - Configure daily opening and closing hours for all 7 days.
  - Add and manage midday break intervals (e.g., lunch 13:30 - 14:30).
  - Add and manage salon holidays / closed dates.
- **Gallery Manager**: Drag-and-drop / upload images with category tagging and featured flags.
- **Salon Settings**: Live configuration of salon name, phone, WhatsApp number, Instagram URL, TikTok URL, address, and announcement banner text.

---

## 🛠 Technology Stack

- **Backend**: Python 3.13 + FastAPI + Uvicorn
- **Database**: SQLite with Write-Ahead Logging (WAL) and atomic transactions
- **Authentication**: JWT (`python-jose`) + `bcrypt`
- **Frontend**: Vanilla ES Modules, Tailwind CSS, Lucide-style luxury vector iconography
- **Testing**: `pytest` + `httpx` (FastAPI TestClient)
- **Zero Node.js dependency required** — Runs out-of-the-box on standard Python 3.

---

## 🚀 Quick Start

### 1. Installation
Ensure Python 3.10+ is installed:
```powershell
pip install -r requirements.txt
```

### 2. Launch the Application
Run the bootstrap script:
```powershell
python run.py
```

The application will start on:
- **Public Website**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Admin Portal**: [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)
- **API Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 👑 Default Admin Credentials

| Field | Value |
|---|---|
| **URL** | `http://127.0.0.1:8000/admin` |
| **Username** | `admin` *(or `admin@blossomdreams.com`)* |
| **Password** | `BlossomAdmin2025!` |

*You can change your password anytime directly in the Admin Dashboard under **Settings > Security**.*

---

## ☁️ Production Deployment (100% Free)

The app is ready to deploy on a **free** stack built for FastAPI + PostgreSQL + persistent image uploads:

| Service | Role | Free tier |
|---|---|---|
| **Render** | FastAPI web service + automatic HTTPS | free, sleeps after 15 min idle |
| **Neon** 🦒 | PostgreSQL database (persistent, never expires) | free |
| **Supabase Storage** | Image uploads (persistent object storage) | free |

`render.yaml` (Render Blueprint), `Procfile`, and `Dockerfile` are already in the repo.

### 1. Push the code to GitHub
```powershell
git init
git add .
git commit -m "Initial production-ready version"
git remote add origin https://github.com/YOUR_USER/blossom-dreams-lb.git
git push -u origin main
```

### 2. Create a free Neon database
1. Sign up at https://console.neon.tech (free).
2. **New Project** → pick a region near your audience (e.g. EU Central).
3. Click **Connect** → copy the connection string (Direct connection):
   `postgresql://user:pass@ep-xxxx.eu-central-1.aws.neon.tech/blossom?sslmode=require`

### 3. Create a free Supabase project (for uploads)
1. Sign up at https://supabase.com (free).
2. **New Project** → note your **Project URL** (e.g. `https://abc123.supabase.co`).
3. Open **Storage** → **New Bucket** → name it `uploads` → enable **Public bucket**.
4. Open **Project Settings → API Keys** → copy the `service_role` key.

### 4. Deploy on Render
1. Sign up at https://render.com (free, no credit card).
2. Click **New +** → **Blueprint** → select your GitHub repo.
3. Render reads `render.yaml` and asks for the missing values — paste:
   - `DATABASE_URL` → your Neon connection string
   - `PUBLIC_BASE_URL` → your Render URL (e.g. `https://blossom-dreams-lb.onrender.com`)
   - `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` → from step 3
   - `SECRET_KEY` is generated automatically
4. Click **Apply** and wait for the deploy to finish.

🎉 You get a public HTTPS URL automatically: **`https://blossom-dreams-lb.onrender.com`**

> Your admin login (from `ADMIN_USERNAME` / `ADMIN_PASSWORD`) is created on first boot.
> Change the password afterwards under **Admin → Settings → Security**.
> Optional: add your own domain (e.g. `blossomdreams.com`) under the service's
> **Settings → Custom Domains** — free HTTPS is included.

---

## 🧪 Automated Testing

Run the test suite:
```powershell
python -m pytest tests/test_api.py -v
```

All tests verify:
- Health check & public salon endpoints
- Services & category listings
- Dynamic availability slot calculation & break exclusions
- Sunday / holiday closure enforcement
- Atomic double-booking collision prevention (HTTP 409)
- Admin authentication & JWT token validation
- Admin CRUD operations

---

## 📁 Project Structure

```
blossom-dreams-lb/
├── app/
│   ├── main.py                  # FastAPI entry point & lifespan
│   ├── database.py              # SQLite connection & schema DDL
│   ├── models.py                # Pydantic validation schemas
│   ├── auth.py                  # JWT & Bcrypt authentication
│   ├── availability_engine.py   # Dynamic slot & conflict calculator
│   ├── seed_data.py             # Realistic Blossom Dreams initial data
│   └── routers/
│       ├── auth.py              # /api/auth endpoints
│       ├── services.py          # /api/services CRUD
│       ├── categories.py        # /api/categories CRUD
│       ├── offers.py            # /api/offers CRUD
│       ├── bookings.py          # /api/bookings atomic bookings
│       ├── availability.py      # /api/availability slots & config
│       ├── gallery.py           # /api/gallery endpoints
│       ├── settings.py          # /api/settings endpoints
│       └── upload.py            # /api/upload image handler
├── public/
│   ├── index.html               # Public mobile-first website
│   ├── admin/
│   │   └── index.html           # Salon owner admin portal
│   ├── css/
│   │   └── style.css            # Luxury theme styling
│   ├── js/
│   │   ├── api.js               # Unified API client & toasts
│   │   ├── app.js               # Public frontend controller
│   │   ├── booking.js           # 4-step interactive booking wizard
│   │   └── admin.js             # Admin dashboard controller
│   ├── images/                  # Aesthetic cards & branding visuals
│   └── uploads/                 # User-uploaded salon imagery
├── tests/
│   └── test_api.py              # Automated test suite
├── create_placeholders.py       # Image generator utility
├── run.py                       # Single-command launcher
├── requirements.txt             # Python dependencies
└── README.md                    # Documentation
```
