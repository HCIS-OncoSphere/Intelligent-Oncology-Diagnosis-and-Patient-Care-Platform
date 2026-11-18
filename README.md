# Intelligent Oncology Diagnosis and Patient Care Platform (OncoSphere - Phase 2)

A comprehensive healthcare and clinical oncology management platform built with Django REST Framework, React (Vite), and HL7 v2 integration.

```
oncosphere/
├── backend/       Django + DRF + JWT (accounts, patients, appointments, records, billing, reports, integration)
├── hl7_service/   HL7 v2 MLLP server + client (ADT, SIU, ORM, ORU), validation, ACK/NACK
├── frontend/      React (Vite) Single Page Application
├── docs/          Architecture, security and backup documentation
└── scripts/       Maintenance and database backup scripts
```

---

## 👥 Team Contribution & Feature Branching Guide

To ensure clean collaboration across all 6 team members, each member works on their dedicated feature branch and opens a Pull Request (or merges to `main`):

| Member | Feature | Branch Name | Scope / Target Modules |
|---|---|---|---|
| **Member 1** | **Auth & RBAC** | `feature/auth-rbac` | `backend/accounts/` (Custom User, JWT Auth, Permissions) |
| **Member 2** | **Patients Management** | `feature/patient-management` | `backend/patients/` (MRN, Demographics, Patient Profiles) |
| **Member 3** | **Appointments** | `feature/appointments-scheduling` | `backend/appointments/` (Doctor Availability, Booking, Clash Prevention) |
| **Member 4** | **Medical Records & ICD-10** | `feature/medical-records` | `backend/records/` (Encounters, ICD-10 Diagnosis, Prescriptions, Plans) |
| **Member 5** | **Billing & Invoices** | `feature/billing-system` | `backend/billing/` (Service Catalog, Invoices, Payment tracking) |
| **Member 6** | **Analytics & HL7 Service** | `feature/reports-hl7` | `backend/reports/`, `backend/integration/`, `hl7_service/` |

---

## 🚀 Quick Start Guide

### 1. Backend Setup (Python 3.10+)
```bash
cd backend
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py seed            # Available once accounts/records are merged
python manage.py runserver       # http://localhost:8000
```

- **Swagger Documentation:** `http://localhost:8000/api/docs/`
- **OpenAPI Schema:** `http://localhost:8000/api/schema/`

### 2. Frontend Setup (Node 18+)
```bash
cd frontend
npm install
npm run dev                      # http://localhost:5173
```
*Note: Vite dev server is preconfigured to proxy `/api` requests to `http://127.0.0.1:8000`.*

---

## 🧪 Testing
```bash
# Backend unit tests
cd backend
python manage.py test

# HL7 socket tests
cd hl7_service
python -m unittest test_hl7 -v
```
