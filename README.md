# Intelligent Oncology Diagnosis and Patient Care Platform (OncoSphere)

A comprehensive healthcare and clinical oncology management platform built with **Django REST Framework (DRF)**, **React (Vite)**, and **HL7 v2** interoperability standards.

---

## 📁 Project Architecture

```
Intelligent-Oncology-Diagnosis-and-Patient-Care-Platform/
├── backend/                   # Django REST Framework backend
│   ├── accounts/             # Authentication, RBAC (Admin, Clinical, Patient), JWT
│   ├── patients/             # Patient demographics, MRN generation, clinical records
│   ├── config/               # Project settings, URLs, WSGI, CORS & JWT configuration
│   ├── manage.py             # Django management CLI
│   └── requirements.txt      # Python dependencies
├── frontend/                  # React + Vite Single Page Application
│   ├── src/                  # React components and API client
│   ├── package.json          # Node.js dependencies and scripts
│   └── vite.config.js        # Vite dev server configuration & API proxy
├── docs/                      # Architecture, security & Postman collections
└── scripts/                   # Database maintenance & backup scripts
```

---

## 📋 Prerequisites

Ensure you have the following installed before starting:
- **Python**: version 3.10 or higher (tested with Python 3.11, 3.12, and 3.13)
- **Node.js**: version 18 or higher (LTS recommended) and **npm**
- **Git**

---

## 🚀 Step-by-Step Setup Guide

### Step 1: Open Terminal & Navigate to Project

Open your preferred terminal (PowerShell, Command Prompt, or Bash) and navigate to the project directory:

```bash
cd Intelligent-Oncology-Diagnosis-and-Patient-Care-Platform
```

---

### Step 2: Set Up and Run the Backend

1. **Navigate into the backend directory:**
   ```bash
   cd backend
   ```

2. **Create a Python virtual environment:**
   - **On Windows (PowerShell or Command Prompt):**
     ```powershell
     python -m venv .venv
     ```
   - **On macOS / Linux:**
     ```bash
     python3 -m venv .venv
     ```

3. **Activate the virtual environment:**
   - **On Windows (PowerShell):**
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
     *(If script execution is disabled on PowerShell, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first, or use `.venv\Scripts\activate.bat` in Command Prompt)*
   - **On macOS / Linux:**
     ```bash
     source .venv/bin/activate
     ```

4. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   Already set up from before? Run it again: the backend now uses `psycopg` 3 (for its
   connection pool) instead of `psycopg2`, and `argon2-cffi` for password hashing.

5. **Connect to the team's Neon database (required):**
   The whole team works on one shared Neon PostgreSQL database. Copy the template and paste
   the `DATABASE_URL` the team lead sent you privately:
   ```powershell
   Copy-Item .env.example .env   # macOS / Linux: cp .env.example .env
   ```
   **Never commit `.env`**: this repository is public. Without it the backend refuses to start.
   To work offline on a local SQLite file instead, put `USE_SQLITE=1` in `.env`.

6. **Run database migrations:**
   ```bash
   python manage.py migrate
   ```

7. **(Optional) Create an Admin superuser:**
   To access the Django Admin portal and manage accounts via the admin role:
   ```bash
   python manage.py createsuperuser
   ```
   Follow the prompts to set username, email, and password.

8. **Start the Django development server:**
   ```bash
   python manage.py runserver
   ```
   The backend API is now running at **`http://127.0.0.1:8000/`**.

---

### Step 3: Set Up and Run the Frontend

Open a **second terminal window** (keep the backend server running in the first):

1. **Navigate into the frontend directory:**
   ```bash
   cd Intelligent-Oncology-Diagnosis-and-Patient-Care-Platform/frontend
   ```

2. **Install frontend dependencies:**
   ```bash
   npm install
   ```

3. **Start the Vite development server:**
   ```bash
   npm run dev
   ```

4. **Open the application:**
   Open your browser and visit: **`http://localhost:5173`**

> **Note:** The Vite development server is pre-configured to proxy all `/api` requests automatically to `http://localhost:8000`.

---

## 🧪 Running Automated Tests

To run the backend test suite (includes authentication, RBAC, MRN generation, and patient permissions):

1. Make sure your virtual environment is activated in `backend/`:
   ```bash
   cd backend
   python manage.py test accounts patients
   ```

2. To run with detailed test output:
   ```bash
   python manage.py test accounts patients --verbosity=2
   ```

All 19 test cases should pass:
```text
Ran 19 tests in ~35s
OK
```

---

## 📖 API Documentation & Key Endpoints

When the backend server is running, you can explore and test the endpoints directly in your browser:

| Resource | URL | Description |
|---|---|---|
| **Interactive Swagger UI** | `http://localhost:8000/api/docs/` | Interactive OpenAPI documentation & test console |
| **OpenAPI Schema** | `http://localhost:8000/api/schema/` | Raw OpenAPI JSON/YAML schema |
| **Django Admin** | `http://localhost:8000/admin/` | Built-in administration interface |

### Key API Endpoints

- **`POST /api/auth/register/`**: Patient self-registration (creates both user and medical profile)
- **`POST /api/auth/login/`**: Obtain JWT `access` and `refresh` tokens
- **`POST /api/auth/refresh/`**: Refresh expired access token
- **`GET /api/auth/me/`**: Get authenticated user profile (`PATCH` supported for self-updates)
- **`GET /api/patients/`**: List patient records (filtered by role: patients see only their own, clinical/admin see all)
- **`PATCH /api/patients/{id}/`**: Update contact/demographics (protected from unauthorized tampering)
- **`GET /api/users/`**: User management (Admin only)

#### Registration, roles and approval

Roles: `admin` (accounts, doctor requests, settings, audit), `clinical` (doctors), and `patient`.
Admins run billing (invoices, payments and the price list); see `IsBillingStaff` in `accounts/permissions.py`.

- **`POST /api/auth/register/`**: patient sign-up. Besides name, date of birth, email and password it takes `phone`, `address`, `blood_type`, `national_id` (14 digits, optional), `emergency_contact` and `emergency_contact_phone`
- **`POST /api/auth/register/doctor/`** (multipart): a doctor asks for an account with specialty, licence number, experience, education, languages, focus areas and a licence file (PDF/JPG/PNG, 5 MB). The account stays switched off until an admin approves it. A rejected doctor can apply again with the same email
- **`GET /api/admin/doctor-requests/`** (`?status=pending|approved|rejected`), **`POST .../{id}/approve/`**, **`POST .../{id}/reject/`** (body `{"reason": "..."}`), **`GET .../{id}/license/`**: the admin's review queue
- **`POST /api/admin/doctors/`**: an admin creates a doctor account directly. The reply holds a one-time `temporary_password`, and the person must change it at first sign-in (`must_change_password` in `/api/auth/me/`)
- **`POST /api/auth/change-password/`**, **`GET, POST /api/notifications/`** (list / mark as read)

E-mail: with no `EMAIL_HOST` in `backend/.env`, messages are printed in the server console. To send real
mail, set `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` (see `.env.example`).
Public sign-up pages are limited to `REGISTER_RATE` (default 60/hour per IP). Run `python manage.py migrate`
after pulling this change.

#### Appointments (F3) and reports (F7)

Demo data for this slice: `python manage.py seed_appointments` (admin / dr.salma with Mon-Fri 09:00-17:00 / patient1).

- **`GET /api/doctors/`**, **`GET /api/doctors/{id}/slots/?date=YYYY-MM-DD`**: doctors with their weekly hours, and the free 30-minute slots of one day
- **`GET, POST /api/availability/`** (`?doctor=id`): weekly working windows (read: everyone, write: staff)
- **`GET, POST /api/appointments/`**: list (patients see only their own; filters `?status=`, `?date=`, `?doctor=`, `?patient=`, `?upcoming=1`) and book. Booking is refused when it is in the past, outside the doctor's hours or overlaps another booking
- **`POST /api/appointments/{id}/cancel/`**, **`POST /api/appointments/{id}/reschedule/`**: cancel (frees the slot) or move a booking
- **`GET /api/appointments/reminders/`**: tomorrow's scheduled appointments with phone numbers (staff)
- **`GET /api/reports/summary/?days=30`**: dashboard numbers (staff). Billing and diagnosis figures appear once those apps are installed
- **`GET /api/reports/export/?type=appointments|patients|invoices`**: CSV download (staff)

Tests: `python manage.py test appointments reports`. Postman: `docs/postman/2_Appointments_Reports.postman_collection.json`.

---

## ⚙️ Environment Configuration

The backend needs the shared Neon database (`DATABASE_URL` in `backend/.env`) unless `USE_SQLITE=1` is set. You can configure the following environment variables:

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `dev-only-change-me...` | Django secret key |
| `DEBUG` | `1` (True) | Set to `0` for production |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,0.0.0.0` | Comma-separated list of allowed hostnames |
| `CORS_ALLOWED_ORIGINS`| `http://localhost:5173,http://localhost:3000` | Comma-separated allowed frontend origins |
| `DATABASE_URL` | *(empty)* | Full Postgres URL (e.g. Neon's connection string). Wins over `DB_*`. Can live in `backend/.env` (see `backend/.env.example`) |
| `USE_SQLITE` | `0` | Set to `1` to use a local SQLite file instead of Neon (offline work) |
| `DB_POOL` | `1` | Connection pool for `DATABASE_URL`: connections to Neon are opened once and reused, instead of a ~1 s reconnect on every request. Set `0` to turn it off |
| `DB_POOL_MAX` | `4` | Most connections one backend process keeps open to Neon |
| `DB_CONN_MAX_AGE` | `60` | Only used when `DB_POOL=0` |
| `DB_ENGINE` | *(empty)* | Set to `postgres` to use PostgreSQL via the `DB_*` variables |
| `DB_SSLMODE` | `prefer` | Use `require` for Neon when using `DB_*` variables |
| `DB_NAME` | `oncosphere` | PostgreSQL database name |
| `DB_USER` | `postgres` | PostgreSQL username |
| `DB_PASSWORD` | `postgres` | PostgreSQL password |
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `HL7_ENABLED` | `0` | Set `1` to enable HL7 MLLP link |
| `HL7_HOST` | `127.0.0.1` | HL7 server address |
| `HL7_PORT` | `2575` | HL7 MLLP port |

### Moving the shared database to a closer Neon region

The current Neon project is in `us-east-2` (Ohio), so every query from Egypt takes ~160 ms
there and back, and a sign-up makes about 12 of them. A Neon project's region cannot be
changed afterwards, so moving means a new project plus a copy of the data. One person does
this once, for everyone:

1. In the Neon console, create a **new project** in **AWS Europe Central 1 (Frankfurt)** with
   the same Postgres version. Copy its **pooled** connection string (host contains `-pooler`).
2. Add it to `backend/.env` as a new line, keeping the existing `DATABASE_URL` as it is:
   ```
   NEW_DATABASE_URL=postgresql://...-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
   ```
3. Ask the team to stop using the app, then run from the repo root:
   ```powershell
   backend\.venv\Scripts\python.exe scripts\move_neon_region.py
   ```
   The script checks that the new database is empty, copies every row across, and compares
   row counts table by table. Only if they all match does it switch `backend/.env` to the new
   database (the old URL stays there as a comment). The old database is never changed, so a
   failed run can be retried.
4. Restart `runserver`, log in to check, and send the new `DATABASE_URL` to the team privately.
   Delete `backend/neon_backup.json` when you're sure (real patient data; it is git-ignored).
   Keep the old Neon project for a few days in case anything is missing, then delete it.
