# JalRakshak AI — Environmental Intelligence & Disaster Risk Decision Support

> **Product**: Flood and Drought Risk Intelligence & Preparedness Decision-Support System  
> **Region**: Uttar Pradesh, India  
> **Pilot Focus Areas**:
> - **Gorakhpur**: Flood-risk intelligence (Rapti & Rohini River Basins, Eastern UP)
> - **Mahoba**: Meteorological drought intelligence (Bundelkhand Plateau, Ken River Basin)
>
> **Status**: Verified Working Prototype (Phase 6 / Final Delivery).  
> **Decision-Support Notice**: JalRakshak is a decision-support and awareness tool, not an official forecasting authority or replacement for statutory emergency warnings issued by the India Meteorological Department (IMD), Central Water Commission (CWC), or the Uttar Pradesh State Disaster Management Authority (UPSDMA).

---

## 1. Executive Summary & Purpose

**JalRakshak AI** bridges the gap between raw geospatial satellite feeds and ground-level disaster preparedness in Uttar Pradesh. By synthesizing precipitation observations, climatological baselines, and terrain factors, it empowers disaster mitigation officers, relief volunteers, and community coordinators with actionable intelligence.

### Pilot Locations & Indicator Focus

1. **Gorakhpur (Flood Risk Assessment)**:
   - **Hydrological Setting**: Low-elevation alluvial flood plains of the Rapti and Rohini rivers (~84m MSL).
   - **Indicators**: 7-day cumulative rainfall (286 mm, +65.3% departure), 30-day cumulative rainfall (512 mm), 18 wet days (daily precipitation ≥ 2.5 mm), and 94th percentile historical ranking.
   - **Scientific Boundary**: Rainfall accumulation measures meteorological water loading only. It does **not** compute real-time Rapti river gauge stage levels, upstream Nepal barrage releases, or embankment breach inundation depths.

2. **Mahoba (Drought Risk Assessment)**:
   - **Hydrological Setting**: Bundelkhand crystalline fractured-rock plateau (~214m MSL) with low moisture retention.
   - **Indicators**: 90-day cumulative rainfall (62 mm, -58.7% departure), Kharif seasonal deficit (-72.0%), Standardized Precipitation Index (SPI-3: -1.84, Severely Dry), and 22 consecutive dry spell days (< 1.0 mm/day).
   - **Scientific Boundary**: SPI-3 and rainfall deficits measure meteorological drought only. They do **not** directly measure root-zone soil moisture or deep crystalline aquifer depletion without ground sensor telemetry.

---

## 2. System Architecture & Tech Stack

```
   ┌────────────────────────────────────────────────────────────┐
   │                    React 18 + Vite 5 Frontend              │
   │  • Tailwind CSS Dark Theme (Deep Teal/Navy #06141D)        │
   │  • Lucide React Icons & Recharts Accessible Visualizations │
   │  • Typed API Service Layer (TypeScript 5)                  │
   └─────────────────────────────┬──────────────────────────────┘
                                 │ HTTP REST (/api/v1)
                                 ▼
   ┌────────────────────────────────────────────────────────────┐
   │                    FastAPI Python Backend                  │
   │  • Pydantic v2 Schema Validation                           │
   │  • Ingestion & Scientific Indicators Engine                │
   │  • Provenance Registry & Stale Telemetry Detection         │
   │  • Safe Error Shielding (No Traceback/Internal Path Leaks) │
   └───────────────┬────────────────────────────┬───────────────┘
                   │ Local Socket               │
                   ▼                            ▼
   ┌───────────────────────────────┐  ┌─────────────────────────┐
   │    Gemma 4 Local Adapter      │  │ Deterministic Fallback  │
   │ • Prompt-injection defenses   │  │ Grounded Evidence Synthesizer│
   │ • Live runtime status check   │  │ (Active when offline)   │
   └───────────────────────────────┘  └─────────────────────────┘
```

- **Backend**: Python 3.9, FastAPI, Pydantic v2, Pandas, NumPy, SciPy (Gamma distribution fitting for SPI-3).
- **Frontend**: React 18, TypeScript 5, Vite 5, Tailwind CSS, Recharts, Lucide React.
- **AI Engine**: Gemma 4 local inference adapter with prompt injection sanitization, source citations, and deterministic grounded fallback.
- **Geospatial Integrity**: Centroid-based district coordinates (`geometry_status: "centroid_coordinates_only"`), explicit non-forecast disclosures, and distinct measured zero (`0.0 mm`) vs missing telemetry handling.

---

## 3. Security & Operational Hardening (Phase 6)

1. **Safe Error Shielding**:
   - `global_exception_handler` intercepts all unhandled 500 exceptions, logs internal stack traces and paths to secure server logs, and returns a safe sanitized JSON error to clients without revealing filesystem paths, environment variables, or database strings.
2. **Adversarial Prompt-Injection Defenses**:
   - Query sanitization filters input for DAN jailbreaks, system prompt exfiltration, instruction overrides, and rule-bypass attempts, returning an educational security notice without querying backend models.
3. **Out-of-Scope & Absence of Evidence Handling**:
   - Queries requesting non-environmental information (stocks, general trivia, cryptocurrency) are caught and flagged with an evidence boundary notice, directing users to available pilot indicators.
4. **Data Transparency Disclosure**:
   - Explicit inquiries regarding live vs demo data receive immediate provenance confirmation that values are local prototype fixtures (`is_demo_data: true`).
5. **CORS and Secret Management**:
   - Allowed origins are strictly parsed from `CORS_ORIGINS` environment variables.
   - Secrets are kept exclusively server-side and excluded by `.gitignore`.
   - `.env.example` provides clean template variables.
6. **Frontend Resilience**:
   - `apiFetch` handles connection timeouts (8000ms), network dropouts, non-JSON server errors, and abort signals gracefully without crashing the UI.

---

## 4. API Endpoints Reference (`/api/v1`)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Root API status, pilot locations, and demo data disclosure |
| `GET` | `/api/v1/health` | 4-tier diagnostic health reporting (FastAPI, Gemma 4, Freshness, Pipeline) |
| `GET` | `/api/v1/sources` | Complete provenance registry for 4 satellite & reference feeds |
| `GET` | `/api/v1/risk/flood` | Gorakhpur flood-risk indicators (7d/30d cumulative, anomaly, wet days) |
| `GET` | `/api/v1/risk/drought` | Mahoba meteorological drought indicators (SPI-3, deficit %, dry days) |
| `GET` | `/api/v1/dashboard` | Aggregated executive summary for Gorakhpur and Mahoba |
| `GET` | `/api/v1/trends/rainfall` | Time-series rainfall with explicit missing vs zero distinction |
| `GET` | `/api/v1/map/layers` | Centroid-based geospatial feature points with hazard levels |
| `POST` | `/api/v1/assistant/chat` | Gemma 4 grounded explanation endpoint with injection defenses |

---

## 5. Verification & Testing

### Backend Test Suite (Pytest) — 37 Tests Passing
Validates schema contracts, mathematical calculations, geometry disclaimers, timeout handling, safe error shielding, and prompt injection defenses:
```bash
PYTHONPATH=backend ./backend/venv/bin/pytest backend/tests -v
```
**Result**: `37 passed in 0.83s` (100% pass rate).

### Frontend Test Suite (Vitest) — 26 Tests Passing
Validates full user journey, keyboard navigation, chart filtering, offline fallback, export features, and error resilience:
```bash
cd frontend && npm test -- --run
```
**Result**: `26 passed across 5 test suites in 1.55s` (100% pass rate).

### Total Test Coverage: 63 Automated Tests (100% Passing)

### Production Build
```bash
cd frontend && npm run build
```
**Result**: Built cleanly in 1.29s with zero TypeScript compilation errors.

---

## 6. How to Run Locally

### Prerequisites
- Python 3.9+ with `venv`
- Node.js 18+ (tested with Node 22) and npm
- (Optional) Docker & Docker Compose
- (Optional) Ollama with `gemma:4` model

### Option A: Local Development Setup

#### 1. Backend Server Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start FastAPI server on port 8000
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive Swagger API documentation is available at `http://localhost:8000/docs`.

#### 2. Frontend Server Setup
```bash
# In a separate terminal
cd frontend
npm install

# Start Vite dev server on port 5173
npm run dev
```
Open `http://localhost:5173` in your browser.

---

### Option B: Unified Docker Compose Deployment

```bash
# Build and run backend and frontend simultaneously
docker-compose up --build
```
- Frontend application: `http://localhost:5173`
- Backend API & Swagger: `http://localhost:8000/docs`

---

## 7. Production Deployment Checklist

### Verified Items (Ready for Production)
- [x] Environment configuration template created (`.env.example`)
- [x] Sensitive files and secrets excluded from version control (`.gitignore`)
- [x] CORS origins restricted and configurable via `CORS_ORIGINS`
- [x] Unhandled exception handler configured to shield internal paths and tracebacks
- [x] Multi-tier health diagnostic endpoint implemented (`/api/v1/health`)
- [x] Assistant prompt injection defenses tested against adversarial jailbreaks
- [x] Transparent deterministic fallback active when local Gemma runtime is offline
- [x] Point centroid geometry disclaimer explicit (`geometry_status: "centroid_coordinates_only"`)
- [x] Measured zero rainfall (`0.0 mm`) strictly differentiated from missing observation (`null`)
- [x] Frontend builds cleanly with zero TypeScript compilation errors (`dist/` generated)
- [x] 63 automated tests (37 backend + 26 frontend) passing completely

### Unverified / Operational Items (Requires Target Host Setup)
- [ ] Live satellite streaming ingestion (current deployment operates on verified benchmark fixtures `is_demo_data: true`)
- [ ] Dedicated SSL/TLS certificate termination on reverse proxy (Nginx / Cloudflare)
- [ ] Local GPU acceleration for Ollama neural model (runs on deterministic fallback when GPU daemon is offline)
- [ ] District boundary GIS polygon shapefile integration (currently using official Survey of India centroid coordinates)

---

## 8. Hackathon Demo Walkthrough (10-Step Presentation Script)

1. **Application Shell & Branding**:
   - Open `http://localhost:5173`. Point out the light sidebar, deep navy theme, and persistent "Decision-Support Prototype: UP Pilot 2026" disclaimer banner.
2. **Dashboard Overview**:
   - Show the Gorakhpur 7-day rainfall (+65.3% departure) and Mahoba Kharif deficit (-72%) quick metric cards.
3. **Gorakhpur Flood Assessment**:
   - Navigate to *Flood Assessment*. Note the Rapti Basin context, 286 mm 7-day accumulation, and the **Scientific Transparency Note**: *"Rainfall accumulation alone does NOT determine river stage or embankment breaches."*
4. **Mahoba Drought Assessment**:
   - Navigate to *Drought Assessment*. Highlight the Standardized Precipitation Index (**SPI-3: -1.84, Severely Dry**), 22 consecutive dry spell days, and the hard-rock aquifer limitation disclosure.
5. **Interactive Risk Map**:
   - Navigate to *Risk Map*. Toggle between *All Hazards*, *Flood Focus*, and *Drought Focus*. Show the centroid coordinates disclaimer and switch to the **Accessible District Registry Table** for keyboard/screen-reader navigation.
6. **Rainfall Trends & Zero vs Missing Distinction**:
   - Navigate to *Rainfall & Trends*. Toggle aggregation between *Daily*, *Weekly*, and *Monthly*. Demonstrate that `0.0 mm` represents a verified dry day while missing telemetry is labeled as missing. Click **JSON** or **CSV** to export verified data.
7. **Data Transparency & Scientific Methodology**:
   - Navigate to *Data Sources*. Show the 4 registered datasets (GPM IMERG, CHIRPS v2.0, SRTM DEM, UPSDMA) and review the 6-part mathematical derivation of SPI-3 and indicator boundaries.
8. **System Monitoring (4-Tier Separation)**:
   - Navigate to *System Monitoring*. Highlight that FastAPI Backend is Online, while Gemma 4 Runtime honestly reports **Deterministic Fallback Active** (proving live AI is never falsely reported as healthy merely because HTTP responds).
9. **Gemma 4 Grounded Assistant**:
   - Navigate to *AI Assistant*. Click *"Why is flood risk high in Gorakhpur?"*. Show the grounded explanation with specific numbers and official document citations.
   - Type *"Is this live or demo data?"* to demonstrate the automated data transparency disclosure.
10. **Preparedness & Responsible Use**:
    - Navigate to *Preparedness*. Review official helplines (1070, 1077, 112) and action checklists. Emphasize that links are labeled as **Advisory References**, concluding with the responsible-use commitment to direct citizens to official government authorities.
