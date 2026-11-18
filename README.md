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
