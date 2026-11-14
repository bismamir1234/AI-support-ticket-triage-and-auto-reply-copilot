# Engineering Project Handover Document
## AI Support Ticket Triage & Auto-Reply Copilot

**Handover Date:** November 14, 2026  
**Project Version:** 2.0.0-final  
**Lead AI Engineer / Author:** Antigravity AI Assistant  
**Recipient:** Engineering Team Lead & Support Operations Group  
**Repository Branch:** `main`  
**GitHub Repository:** [bismamir1234/AI-support-ticket-triage-and-auto-reply-copilot](https://github.com/bismamir1234/AI-support-ticket-triage-and-auto-reply-copilot)  

---

## 1. Executive Summary & Project Overview

The **AI Support Ticket Triage & Auto-Reply Copilot** is an enterprise-grade customer support platform engineered to automate high-volume ticket triage, enforce strict SLA prioritization, and draft empathetic, policy-grounded customer responses with mandatory Human-in-the-Loop (HITL) review.

### Primary Business Objectives Achieved:
1. **Accelerated Triage:** Reduces incoming support ticket classification time from minutes to under 2 seconds using Groq-accelerated LLMs (`llama-3.3-70b-versatile`).
2. **Strict Policy Grounding:** AI responses are strictly anchored in internal company operating policies (`policy.json`), preventing unauthorized refund commitments or false delivery claims.
3. **Mandatory Human-in-the-Loop:** Support agents retain full autonomy to edit, approve, or reject draft replies prior to mock dispatch.
4. **Enterprise Security:** Active guardrails against prompt injection, unauthorized monetary requests, and secret leakage.
5. **Operational Auditability:** SQLite database persistence supporting real-time KPI dashboards and 10-field CSV and structured JSON batch exports.

---

## 2. Implemented Feature Inventory

| Module / Feature | Description | Implementation Status |
|---|---|---|
| **AI Ticket Classification** | Multi-class classification into Order Issue, Refund, Technical Support, and General Inquiry with secondary category tagging. | **Completed & Verified** |
| **Urgency Detection (P1–P4)** | Dynamic prioritization: P1 (Critical/High), P2 (Medium), P3 (Low), P4 (Informational) with visual color badges and flame icons. | **Completed & Verified** |
| **Customer Sentiment Analysis** | Granular sentiment identification (Angry, Frustrated, Highly Urgent, Neutral, Positive) with anti-sarcasm guardrails. | **Completed & Verified** |
| **Entity Extraction** | Automated regex and LLM extraction of Order IDs (`ORD-XXXXX`), error codes (`500`, `402`), dates, and account emails. | **Completed & Verified** |
| **Missing Entity Detection** | Detection of missing mandatory information (e.g., missing Order ID on refund requests) prompting clarification before action. | **Completed & Verified** |
| **Policy-Grounded Reply Generator** | Multi-policy draft generation anchored in `POL-ORDER`, `POL-REFUND`, `POL-TECH`, and `POL-GENERAL`. | **Completed & Verified** |
| **Manual Draft Editor** | Interactive textarea with live character counter, unsaved edit detection, and undo/discard capabilities. | **Completed & Verified** |
| **Human Approval & Rejection** | Multi-state workflow: **Approve & Send** (with mock dispatch notice) and **Reject Draft** (flagging ticket for manual drafting). | **Completed & Verified** |
| **Ticket Resolution** | One-click resolution updating SQLite database and refreshing real-time dashboard statistics. | **Completed & Verified** |
| **Security Guardrails** | Untrusted XML input isolation, prompt injection neutralization, unauthorized refund dollar blocks, and secret redacting. | **Completed & Verified** |
| **Data Export Engine** | One-click export for both standard Phase 6 CSV, comprehensive 10-field Batch Log CSV, and structured JSON. | **Completed & Verified** |
| **Modern SaaS UI & Dark Mode** | React 19 UI with responsive sidebar, live KPI cards, and persistent light/dark mode theme toggle. | **Completed & Verified** |

---

## 3. System Architecture & Component Interactions

```
+────────────────────────────────────────────────────────────────────────+
|                           REACT 19 FRONTEND                            |
|  - Real-Time Inbox       - AI Copilot Panel     - Interactive Editor   |
|  - P1-P4 Urgency Badges  - Security Alerts      - Dual CSV/JSON Export |
+───────────────────────────────────┬────────────────────────────────────+
                                    │ HTTP / REST APIs
                                    ▼
+────────────────────────────────────────────────────────────────────────+
|                           FASTAPI BACKEND                              |
|  ┌─────────────────────┐  ┌─────────────────────┐  ┌────────────────┐  |
|  │  Security Guardrail │  │   Ticket Analyzer   │  │   Auto-Reply   │  |
|  │  - XML Isolation    │  │   - Pydantic v2     │  │   - Policy     │  |
|  │  - Injection Scan   │  │   - P1-P4 Triage    │  │     Grounding  │  |
|  │  - Post-Validation  │  │   - Entity Engine   │  │   - SLA Target │  |
|  └─────────────────────┘  └─────────────────────┘  └────────────────┘  |
+───────────────────┬──────────────────────────────────┬─────────────────+
                    │                                  │
                    ▼                                  ▼
      +───────────────────────────+      +───────────────────────────+
      |      GROQ CLOUD API       |      |     SQLITE PERSISTENCE    |
      |   Llama 3.3 70B Versatile |      |      SQLAlchemy 2.0       |
      |  (Deterministic Fallback) |      |   (Tickets & Revisions)   |
      +───────────────────────────+      +───────────────────────────+
```

---

## 4. Key Technologies & Libraries

### Frontend:
- **Framework:** React 19.0.0
- **Build Tool:** Vite 8.3.8
- **Icons:** Lucide React (`lucide-react`)
- **Styling:** Custom CSS SaaS Design System with responsive variables and Dark Mode support
- **State Management:** React Hooks (`useState`, `useEffect`, `useMemo`)

### Backend:
- **Framework:** FastAPI 0.115+
- **ASGI Server:** Uvicorn
- **AI Inference:** Groq Python SDK (`groq`) using `llama-3.3-70b-versatile`
- **Data Validation:** Pydantic v2 & Pydantic Settings
- **Database & ORM:** SQLite 3 via SQLAlchemy 2.0 ORM
- **Testing:** Pytest 9.2.0, Starlette TestClient

---

## 5. Directory & File Reference Map

```
AI support ticket triage and auto-reply copilot/
├── backend/                               # FastAPI Python Backend
│   ├── app/
│   │   ├── config.py                      # Environment configuration & settings
│   │   ├── database.py                    # SQLite engine & session management
│   │   ├── models.py                      # Ticket SQLAlchemy ORM model
│   │   ├── schemas.py                     # Pydantic v2 schemas for API contracts
│   │   ├── main.py                        # FastAPI application entrypoint & middleware
│   │   ├── routers/
│   │   │   └── tickets.py                 # REST API endpoints (CRUD, triage, exports)
│   │   └── services/
│   │       ├── security.py                # Security guardrails & injection defense
│   │       ├── ticket_analyzer.py         # AI categorization, priority, sentiment, entities
│   │       ├── auto_reply_generator.py    # Policy grounding & draft generator
│   │       ├── ticket_service.py          # SQLite persistence, approval, resolution & exports
│   │       └── exceptions.py              # Sanitized exception hierarchy (no leaked secrets)
│   ├── tests/                             # Comprehensive test suites
│   │   ├── test_security_and_validation.py # 18 security & validation tests
│   │   ├── test_ten_synthetic_tickets.py  # 10 synthetic edge cases & benchmarks
│   │   ├── test_phase4_auto_reply.py      # Policy grounding & SLA tests
│   │   └── test_phase6_ticket_management.py # Draft editing, reject/approve & export tests
│   ├── policy.json                        # Official customer support policy definitions
│   ├── requirements.txt                   # Backend Python dependencies
│   └── tickets.db                         # Local SQLite database
├── frontend/                              # React 19 Client
│   ├── src/
│   │   ├── components/
│   │   │   ├── Badges.jsx                 # Urgency (P1-P4), Category, Sentiment & Status badges
│   │   │   ├── Sidebar.jsx                # Responsive navigation & status indicator
│   │   │   └── StatsCards.jsx             # Top KPI summary cards
│   │   ├── api.js                         # API fetch client & export download helpers
│   │   ├── App.jsx                        # Main workspace layout & state management
│   │   └── index.css                      # SaaS design system & Dark Mode styling
│   ├── package.json                       # Frontend dependencies & scripts
│   └── vite.config.js                     # Vite dev server & proxy settings
├── evidence/                              # Verification Artifacts & Test Logs
│   ├── exports/                           # Actual CSV and JSON exports
│   │   ├── sample_batch_tickets_log.csv   # 10-field batch processing log
│   │   └── actual_tickets_export.json     # Complete structured JSON export
│   ├── screenshots/                       # 22 automated high-resolution UI captures
│   └── test_results.json                  # Machine-readable test execution records
├── sample_batch_tickets_log.csv           # Root copy of 10-field batch processing log
├── .env.example                           # Root environment variable template
├── QA_VERIFICATION_CHECKLIST.md           # 16-suite QA verification checklist
├── DEMO_SCRIPT.md                         # 5-7 minute live demonstration script
├── PROJECT_HANDOVER.md                    # This document
└── README.md                              # Complete system setup & architecture manual
```

---

## 6. Setup & Verification Instructions

### 1. Backend Startup:
```bash
# Navigate to backend directory
cd backend

# Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Configure environment variables
# Copy .env.example to .env and insert your GROQ_API_KEY
cp .env.example .env

# Start FastAPI development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
*Backend runs at:* `http://localhost:8000` (Swagger UI at `/docs`)

### 2. Frontend Startup:
```bash
# In a separate terminal, navigate to frontend directory
cd frontend

# Install Node dependencies (if first time)
npm install

# Start Vite development server
npm run dev
```
*Frontend runs at:* `http://localhost:5173`

### 3. Automated Test Execution:
```bash
# Run deterministic unit and integration test suite
backend\venv\Scripts\python.exe -m pytest backend/tests -v -m "not live_groq"

# Run full live Groq benchmark tests (requires active API key)
backend\venv\Scripts\python.exe -m pytest backend/tests/test_ten_synthetic_tickets.py -v
```

---

## 7. Automated Test Results Summary

| Test Suite | Total Tests | Passed | Execution Time |
|---|---|---|---|
| `test_security_and_validation.py` | 18 | 18 | 0.95s |
| `test_ten_synthetic_tickets.py` (Deterministic) | 10 | 10 | 0.89s |
| `test_phase6_ticket_management.py` | 8 | 8 | 47.3s (w/ live AI) |
| `test_phase4_auto_reply.py` | 4 | 4 | 18.2s (w/ live AI) |
| `test_five_scenarios.py` | 6 | 6 | 24.1s (w/ live AI) |
| **All Test Suites Combined** | **46** | **46** | **100% Pass** |

---

## 8. Known Operational Limitations

1. **Groq Free-Tier Rate Limits:** The Groq free tier imposes a limit of ~30 requests per minute and 6,000 tokens per minute. Running 40+ live requests back-to-back in rapid succession can trigger HTTP 429. The application gracefully falls back to deterministic rule-based replies when `ALLOW_RULE_FALLBACK=true`.
2. **Ambiguous Edge Cases:** Highly vague tickets (e.g. *"it's broken"*) cannot be categorized with certainty; the system is designed to flag these with `needs_clarification=True` and ask the customer for details rather than hallucinating.
3. **No Automated Email Transmission:** By strict project design, no real emails are dispatched. The system records approvals and provides a demonstration notice to ensure safety in test environments.
4. **Policy Scope:** AI responses depend entirely on `backend/policy.json`. If a new product category or warranty rule is added, `policy.json` must be updated to enable the model to ground replies accurately.

---

## 9. Instructions for the Team Lead

### Immediate Next Actions:
1. **Review Verification Checklist:** Inspect `QA_VERIFICATION_CHECKLIST.md` to confirm all 10 synthetic test cases pass.
2. **Run Live Demo:** Follow `DEMO_SCRIPT.md` to execute the 5–7 minute live demonstration workflow.
3. **Inspect Batch Log Export:** Review `sample_batch_tickets_log.csv` to verify that all 10 required audit fields are present.
4. **Production Deployment Plan:**
   - For Docker deployment, containerize using `uvicorn app.main:app` with a production ASGI server.
   - Set up an enterprise Groq tier or private LLM endpoint in `backend/.env`.
   - Transition SQLite to PostgreSQL by updating `DATABASE_URL` in `backend/app/config.py` (SQLAlchemy models are dialect-agnostic).
