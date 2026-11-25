# EnterpriseIQ — AI-Powered Business Intelligence Management System

EnterpriseIQ transforms raw business documents, operational records, and financial KPIs into evidence-backed insights, anomaly alerts, forecasts, executive reports, and closed-loop corrective actions.

## Key Capabilities
- **10 Signature Screens:** Command Center, Business Analytics, AI Intelligence (Root Cause Analysis), Risk Observatory, Department Insights, Reports Studio (CSV/Markdown export), Action Center (Kanban), Knowledge Hub (drag-and-drop ingestion + validation), AI Copilot (RAG + citations), and Settings (RBAC + Audit Logs).
- **Stage 2 Processing Pipeline:** Extracts PDF (`PyMuPDF`), Word (`python-docx`), Excel (`openpyxl`), and CSV (`pandas`) files, flags missing values & duplicate rows without silently discarding them, and indexes chunks.
- **Stage 3 Analytics & AI:** Scikit-learn IsolationForest + Z-score anomaly detection, Statsmodels Holt linear trend forecasting with 90% uncertainty bounds, and Gemini OpenAI-compatible RAG Copilot (with a clearly labeled Demonstration/Grounded mode when `LLM_API_KEY` is unset).
- **Multi-Tenant Security:** JWT authentication, 4-role backend RBAC (`ceo`, `department_manager`, `business_analyst`, `system_admin`), organization-level data isolation, and compliance audit logs.

## Demo Accounts (Seeded Automatically on First Boot)
Organization: **Meridian Apex Corp (Demo)** — Scenario: Q3–Q4 revenue decline ($1.56M → $1.31M), rising OpEx ($910K → $1.07M), and climbing customer complaints (118 → 246/mo).

| Role | Email | Password |
| :--- | :--- | :--- |
| CEO / Managing Director | `ceo@meridian-demo.com` | `DemoPass123!` |
| Department Manager (Ops) | `ops.manager@meridian-demo.com` | `DemoPass123!` |
| Business Analyst | `analyst@meridian-demo.com` | `DemoPass123!` |
| System Administrator | `admin@meridian-demo.com` | `DemoPass123!` |

## Setup Instructions (Windows — PowerShell)
1. **Prerequisites:** Install Python 3.11+, Node.js 20+, and optionally Docker Desktop.
2. **Configure environment:**
   ```powershell
   Copy-Item .env.example .env
   # Optionally add your Gemini API key in LLM_API_KEY
   ```
3. **Start Backend (FastAPI):**
   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   alembic upgrade head
   uvicorn app.main:app --reload --port 8000
   ```
   Swagger API Docs: `http://localhost:8000/docs`
4. **Start Frontend (React + Vite) in a new PowerShell window:**
   ```powershell
   cd frontend
   npm install
   npm run dev
   ```
   Open `http://localhost:5173`.

## Setup with Docker Compose (All Platforms)
```bash
cp .env.example .env
docker compose up --build
```

## API Documentation Overview
- **Auth & Settings:** `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, `GET /api/notifications`, `GET /api/settings/users`, `GET /api/settings/audit-logs`
- **Dashboard & Departments:** `GET /api/dashboard/overview`, `GET /api/dashboard/trends`, `GET /api/departments`, `GET /api/departments/{id}`
- **Knowledge Hub:** `POST /api/documents/upload`, `GET /api/documents`, `GET /api/documents/{id}`, `GET /api/documents/{id}/status`
- **Analytics & AI:** `GET /api/analytics/kpis`, `POST /api/analytics/analyze`, `GET /api/analytics/forecasts`, `GET /api/analytics/anomalies`, `POST /api/ai/ask`, `POST /api/ai/analyze`, `GET /api/ai/insights`
- **Risks, Reports & Actions:** `GET /api/risks`, `GET /api/risks/{id}`, `POST /api/reports/generate`, `GET /api/reports`, `GET /api/reports/{id}/export?fmt=csv|md`, `POST /api/actions`, `GET /api/actions`, `PATCH /api/actions/{id}`

## Running Tests
```bash
cd backend
pytest -v
```
