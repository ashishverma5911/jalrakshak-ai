# JalRakshak AI — Final Submission Overview
## Neural Storm 2026: AI/ML Hackathon
**Project Name:** JalRakshak AI — Environmental Intelligence & Disaster Risk Decision Support  
**Author:** Ashish Kumar Verma  
**Repository Working Directory:** `/Users/ashish/Downloads/JalRakshak A.I.`  
**Feature Branch:** `feature/phase-3c5-risk-attribution`  
**Status:** **SUBMISSION READY (290/290 Automated Tests Passing, 100% Verified)**  

---

## 1. Executive Summary & Purpose

JalRakshak AI is a geospatial environmental intelligence and disaster risk decision-support platform designed for Uttar Pradesh, India. Developed in accordance with the *Neural Storm 2026 Research Brief*, it bridges the gap between raw geospatial satellite telemetry, Numerical Weather Prediction (NWP) model outputs, and ground-level disaster preparedness.

### The Two Pilot Design
1. **Gorakhpur (Flood Risk Intelligence)**:
   - **Hydrological Setting**: Lowland alluvial floodplains of the Rapti and Rohini River basins (~84m MSL).
   - **Indicators**: 7-day cumulative rainfall, 30-day accumulation, historical percentile ranking, terrain vulnerability coefficient ($0.88$), and authoritative IMD/UPSDMA official alerts.
   - **Scientific Boundary**: Rainfall accumulation evaluates meteorological water loading. It does **not** compute real-time river stage levels, upstream Nepal barrage releases, or embankment breach inundation depths.

2. **Mahoba (Meteorological Drought Intelligence)**:
   - **Hydrological Setting**: Bundelkhand crystalline fractured-rock plateau (~214m MSL) characterized by low moisture retention and steep runoff.
   - **Indicators**: 90-day cumulative rainfall, Kharif seasonal monsoon deficit, Standardized Precipitation Index (SPI-3 via 2-parameter Gamma MLE fitting), consecutive dry spell days ($< 1.0\text{ mm/day}$), and authoritative UPSDMA drought advisories.
   - **Scientific Boundary**: SPI-3 and seasonal deficits evaluate meteorological drought. They do **not** directly measure root-zone soil moisture or deep crystalline aquifer depletion without ground sensor telemetry.

---

## 2. Core Credibility & Scientific Integrity Invariants

In strict adherence to the *Neural Storm 2026 Research Brief*:
1. **Never Misrepresent Estimates as Warnings**: JalRakshak clearly distinguishes derived environmental risk estimates from statutory government early warnings issued by IMD, CWC, or UPSDMA.
2. **Measured Zero vs. Missing Data**: A measured $0.0\text{ mm}$ precipitation observation is strictly distinguished from missing or uncalculated telemetry (`null`), preventing systematic undercounting or misattribution.
3. **Decoupled Historical Replay**: Historical replays (e.g., retrospective assessment on 28 October 2026) are explicitly flagged as `[Historical Replay]`, with past advisories marked as `(INACTIVE)`. Replays cannot masquerade as live operational alerts, and `generated_at` strictly reports server wall-clock execution time.
4. **Insufficient Evidence Safeguard**: Incomplete meteorological indicators without an active advisory classify as `pending` (with badge `PENDING — INSUFFICIENT DATA`), never default-coerced to `low`.
5. **Multi-District Candidate Isolation**: Unonboarded candidate districts (e.g., Lucknow, Patna, Gaya, Varanasi) are strictly isolated with `DATA_PENDING` status and zero data bleed from calibrated pilot models.

---

## 3. System Architecture & Tech Stack

```
   ┌────────────────────────────────────────────────────────────┐
   │                    React 18 + Vite 5 Frontend              │
   │  • Accessible Visualizations (Recharts, Lucide React)      │
   │  • Multi-District Selector & Candidate Isolation           │
   │  • Provenance Badges (LIVE_MODEL, CACHED, DEMO, PENDING)   │
   │  • Historical Replay Banners & Advisory Validity Displays  │
   └─────────────────────────────┬──────────────────────────────┘
                                 │ HTTP REST (/api/v1)
                                 ▼
   ┌────────────────────────────────────────────────────────────┐
   │                    FastAPI Python Backend                  │
   │  • Pydantic v2 Contract Validation                         │
   │  • Open-Meteo NWP Ingestion with 3-hr TTL / 30s Cooldown   │
   │  • SPI-3 Gamma Distribution MLE Calibration Engine         │
   │  • Official Advisory Temporal Boundary Validator           │
   │  • Safe Exception Shielding (Zero Path / Stack Leaks)      │
   └───────────────┬────────────────────────────┬───────────────┘
                   │ Local Socket / API         │
                   ▼                            ▼
   ┌───────────────────────────────┐  ┌─────────────────────────┐
   │    Gemma 4 Neural Adapter     │  │ Deterministic Fallback  │
   │ • Prompt-injection defenses   │  │ Grounded Evidence Synthesizer│
   │ • Multi-tier health monitoring│  │ (Active when offline)   │
   └───────────────────────────────┘  └─────────────────────────┘
```

- **Backend**: Python 3.9, FastAPI, Pydantic v2, Pandas, NumPy, SciPy (Gamma distribution fit), SQLAlchemy, Alembic.
- **Frontend**: React 18, TypeScript 5, Vite 5, Tailwind CSS, Lucide React, Recharts.
- **AI Engine**: Hosted Gemma 4-26B adapter with prompt-injection sanitization, evidence boundaries, and deterministic grounded fallback.
- **Deployment**: Zero-cost (₹0) Render Blueprint (`render.yaml`).

---

## 4. Live Deployed Environments

| Service | Environment URL | Description |
| :--- | :--- | :--- |
| **Frontend Application** | `https://jalrakshak-frontend-ymzk.onrender.com` | Production React 18 SPA (Vite, Global CDN) |
| **Backend REST API** | `https://jalrakshak-api-fv5z.onrender.com` | Production FastAPI ASGI Container |
| **Interactive API Docs** | `https://jalrakshak-api-fv5z.onrender.com/docs` | Live Swagger UI Documentation |
| **Diagnostic Health** | `https://jalrakshak-api-fv5z.onrender.com/api/v1/health` | 4-Tier Diagnostic Health Endpoint |

---

## 5. Verification & Test Suite Results

### 5.1 Backend Test Suite (Pytest) — 245/245 Passing (100%)
- **Test Command**: `PYTHONPATH=backend ./backend/venv/bin/pytest backend/tests/ -v`
- **Coverage Highlights**:
  - Schema contracts, physical boundary checks, and spatial geometry disclaimers.
  - 90-day missing-data safeguards and false 100% anomaly prevention.
  - Kharif monsoon 100-day coverage minimums ($\ge 82\%$).
  - Official advisory temporal validity across all 6 boundary dates (30 Sep, 1 Oct, 28 Oct, 31 Oct, 1 Nov, 4 Nov).
  - Rate limiting, sliding-window cache cooldowns, and exception shielding.
- **Result**: `245 passed in 5.5s` (0 failures).

### 5.2 Frontend Test Suite (Vitest) — 45/45 Passing (100%)
- **Test Command**: `export PATH="/Users/ashish/.local/node-v22/bin:$PATH" && cd frontend && npm test -- --run`
- **Coverage Highlights**:
  - Multi-district selection and candidate isolation with zero data bleed.
  - Dynamic risk card rendering (`high`, `moderate`, `low`, `pending`).
  - Historical replay banner rendering and advisory expiration labels.
  - Scientific dataset uploads and quarantine management.
  - Offline resilience and prompt injection defense UI flows.
- **Result**: `45 passed across 10 test suites in 2.6s` (0 failures).

### 5.3 Production Build Verification
- **Build Command**: `cd frontend && npm run build` (`tsc && vite build`)
- **Result**: Production bundle generated in 1.27s with zero TypeScript compilation warnings or errors.

---

## 6. Hackathon 10-Step Evaluation Walkthrough

Follow this script to demonstrate the prototype during jury evaluation:

1. **Dashboard & Regional Scoping**:
   - Navigate to `/`. Note the persistent disclaimer banner: *"Decision-Support Prototype: UP Pilot 2026"*.
   - Review the executive quick metrics comparing Gorakhpur flood conditions against Mahoba drought indicators.
2. **Gorakhpur Flood Assessment**:
   - Navigate to *Flood Assessment*. Note the Rapti Basin hydrological setting, 7-day loading, terrain vulnerability ($0.88$), and the explicit non-inundation boundary disclaimer.
3. **Mahoba Drought Assessment**:
   - Navigate to *Drought Assessment*. Observe the Standardized Precipitation Index (**SPI-3**), Kharif monsoon departure, and Bundelkhand hard-rock groundwater limitation notes.
4. **Authoritative Advisory Attribution**:
   - Review the official advisory attribution card showing bulletin registration, authority (UPSDMA/IMD), validity period, and operational status.
5. **Historical Replay Transparency**:
   - Test a retrospective historical evaluation. Observe the purple **Historical Replay Simulation Banner**, the `[Historical Replay]` primary driver prefix, and the `(INACTIVE)` operational advisory flag.
6. **Candidate District Isolation**:
   - Switch district to *Gaya* or *Varanasi*. Verify that no pilot scores or observations are leaked: status cleanly reports `DATA_PENDING` with zero data bleed.
7. **Live NWP Telemetry & Refresh**:
   - Switch data mode to *Live NWP*. Inspect the Open-Meteo representative-point centroid estimates and observe the 30-second anti-spam cooldown protection on manual refresh.
8. **Rainfall Trends & Zero vs Missing Distinction**:
   - Navigate to *Rainfall Trends*. Toggle aggregation between *Daily*, *Weekly*, and *Monthly*. Demonstrate that $0.0\text{ mm}$ represents a verified dry day while missing telemetry is labeled as missing (`null`). Export data to JSON/CSV.
9. **Scientific Data Sources & Provenance**:
   - Navigate to *Data Sources*. Review the registered feeds (GPM IMERG, CHIRPS v2.0, SRTM DEM, UPSDMA) and inspect the mathematical derivations of SPI-3 and risk thresholds.
10. **Gemma 4 Grounded Assistant**:
    - Navigate to *AI Assistant*. Ask *"Why is flood risk high in Gorakhpur?"* to observe grounded citations with numbers. Ask *"Is this live or demo data?"* to verify automated transparency disclosure.
