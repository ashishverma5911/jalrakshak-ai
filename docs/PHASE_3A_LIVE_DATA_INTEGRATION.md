# JalRakshak AI — Phase 3A: Live Environmental Data Integration

## 1. Executive Summary & Objective

Phase 3A integrates real external Numerical Weather Prediction (NWP) model data into the JalRakshak AI decision-support platform while strictly adhering to a **₹0/month additional infrastructure budget** and **zero regression** against existing Milestone 8 functionality.

The integration establishes an operational, request-triggered bridge to the official Open-Meteo Weather Forecast API (`https://api.open-meteo.com/v1/forecast`), providing district-level hourly meteorological estimates and 7-day numerical forecasts for precipitation, 2m air temperature, relative humidity, 10m wind speed, and reference FAO-56 evapotranspiration (ET0).

```
                           +----------------------------------------+
                           |   Open-Meteo Forecast API (ECMWF/GFS)  |
                           +----------------------------------------+
                                              |
                                              | HTTPS / JSON (bounded 10s)
                                              v
+---------------------------------------------------------------------------------------+
|  Backend (FastAPI)                                                                    |
|                                                                                       |
|   +------------------------------------+    +-------------------------------------+   |
|   |    OpenMeteoForecastAdapter        |    |     EnvironmentalCacheService       |   |
|   |  - Centroid coordinate resolution  |    |  - Request-triggered lazy lookup    |   |
|   |  - Physical bounds validation      |--->|  - 3-hour TTL & 24-hour stale limit |   |
|   |  - Zero vs missing null semantics  |    |  - asyncio.Lock concurrency guard   |   |
|   |  - Forecast vs near-current split  |    |  - 30s anti-spam refresh cooldown   |   |
|   +------------------------------------+    +-------------------------------------+   |
|                     |                                          |                      |
|                     v                                          v                      |
|   +------------------------------------+    +-------------------------------------+   |
|   |  Risk Engines (Flood & Drought)    |    |  API Endpoints (/api/v1/environmental) |
|   |  - mode='live' -> LIVE_MODEL mode  |    |  - GET /environmental/live          |   |
|   |  - District centroid attribution   |    |  - GET /environmental/status        |   |
|   |  - Open-Meteo CC-BY 4.0 provenance |    |  - POST /environmental/refresh      |   |
|   +------------------------------------+    +-------------------------------------+   |
+---------------------------------------------------------------------------------------+
                                              |
                                              | JSON Responses
                                              v
+---------------------------------------------------------------------------------------+
|  Frontend (React + Vite + Tailwind CSS)                                               |
|                                                                                       |
|   - DataProvenanceBadge: LIVE_MODEL (emerald pulse), PROVIDER_ERROR, NWP FORECAST     |
|   - MainDashboardView: Live Environmental NWP Telemetry card with 1-click refresh     |
|   - DataSourcesView: Registered Open-Meteo forecast entry under CC-BY 4.0             |
|   - SystemMonitoringView: Live pipeline monitor & system status diagnostics          |
+---------------------------------------------------------------------------------------+
```

---

## 2. Scientific Principles & Data Invariants

1. **Representative-Point Centroid Estimates vs In-Situ Gauges:**
   - Numerical weather prediction (NWP) model outputs are evaluated at the exact geometric centroid coordinates of the district administrative boundary (e.g., `26.7606°N, 83.3732°E` for Gorakhpur; `25.2953°N, 79.8630°E` for Mahoba).
   - In accordance with JalRakshak scientific integrity standards, model outputs are explicitly labeled as *representative-point estimates*, never misidentified as in-situ physical rain-gauge telemetry or spatial polygon-averaged flood discharge.
2. **Preservation of Genuine Zero vs Missing Nulls:**
   - An hourly precipitation value of `0.0 mm` represents a genuine observed zero (dry conditions) and is strictly preserved.
   - Missing or corrupted values remain `None` / `null`. They are never coerced or imputed to zero.
3. **Completeness Threshold for Daily Aggregation:**
   - Daily sums require at least **20 valid hourly observations out of 24** ($\ge 83.3\%$). Days with fewer than 20 valid hours evaluate to `null` to prevent severe systematic undercounting.
4. **Temporal Classification (Forecast vs Near-Current Observation):**
   - Hourly records are partitioned relative to retrieval timestamp: records with $t \le t_{\text{retrieval}}$ represent model-analyzed near-current estimates; records with $t > t_{\text{retrieval}}$ represent future forecasts.
5. **Physical Bounds Validation:**
   - Precipitation: $[0, 500]$ mm/hr. Values $< 0$ reject the payload with `AdapterPayloadError`. Values $> 500$ mm/hr are clamped to $500$ mm and flagged as `provisional_extreme`.
   - Temperature: $[-50, 60]$ °C.
   - Relative humidity: $[0, 100]$ %.
   - Wind speed: $[0, 300]$ km/h.
   - Reference evapotranspiration (ET0): $[0, 50]$ mm/hr.

---

## 3. Architecture & Implementation Components

### 3.1 Configuration & Feature Flag (`backend/app/core/config.py`)
- `LIVE_DATA_ENABLED` (boolean, default: `False`): Protects production stability; allows zero-cost offline demo operation by default.
- `OPEN_METEO_FORECAST_URL`: `https://api.open-meteo.com/v1/forecast`
- `LIVE_CACHE_TTL_HOURS`: `3.0` hours.
- `LIVE_STALE_THRESHOLD_HOURS`: `24.0` hours.
- `LIVE_REQUEST_TIMEOUT_SECONDS`: `10.0` seconds.
- `LIVE_MAX_RETRIES`: `2` retries with exponential backoff.

### 3.2 Scientific Source Adapter (`backend/app/pipeline/adapters/open_meteo_forecast.py`)
- Inherits from `ScientificSourceAdapter`.
- Registered as `open_meteo_forecast` in `ScientificSourceRegistry`.
- Implements:
  - `resolve_district_coordinates`: Authoritative lookup from coordinates table or `districts_metadata.json`. Enforces strict district isolation (never borrows adjacent coordinates).
  - `fetch_forecast_raw`: Bounded HTTP client using `httpx` with timeout and retries.
  - `validate_and_parse_hourly`: Validates schema, timestamps, bounds, and forecast flags.
  - `aggregate_hourly_to_daily`: Bounded daily reduction with hourly completeness threshold.
  - `check_connection`: Health check audit endpoint.

### 3.3 Cache & Resilience Layer (`backend/app/services/environmental_cache.py`)
- **Lazy Request-Triggered:** No background worker threads or continuous polling tasks.
- **Cache-First Lookup:** Instant responses (< 5ms) when fresh cache exists ($< 3$ hours).
- **Concurrency Deduplication:** Per-district `asyncio.Lock` ensures that multiple concurrent requests for the same district produce exactly **one** outbound HTTP request.
- **Graceful Fallback:** If Open-Meteo experiences an outage:
  - Cache $< 3$h: returns `CACHED` (fresh).
  - Cache $3$h – $24$h: returns `DATA_STALE` with cached data and honesty notice.
  - Cache $> 24$h or no cache: returns `DATA_PENDING` without fabricating synthetic data.
- **Anti-Spam Cooldown:** Maximum 1 forced refresh per 30 seconds per district.

### 3.4 API Endpoints (`backend/app/api/environmental.py`)
- `GET /api/v1/environmental/live?location=gorakhpur&refresh=false`: Retrieves near-current conditions and 7-day forecasts.
- `GET /api/v1/environmental/status`: Reports feature flag, active cached districts, TTL settings, and connection status.
- `POST /api/v1/environmental/refresh?location=gorakhpur`: Explicitly triggers fresh fetch subject to cooldown.

### 3.5 Engine Integration (`flood_engine.py`, `drought_engine.py`, `trends.py`)
- Support `mode="live"`, setting `data_mode="LIVE_MODEL"`.
- Inserts `open_meteo_forecast` metadata into response `sources` with full licensing (`CC-BY 4.0 Open-Meteo`).
- Appends scientific notes explaining representative-point centroid estimates and model boundaries.

### 3.6 Frontend User Interface
- **`DataProvenanceBadge`:** Enhanced to support `LIVE_MODEL` (emerald pulsing dot), `PROVIDER_ERROR` (rose alert), and `NWP FORECAST` (indigo).
- **`MainDashboardView`:** Dedicated Live Environmental NWP Telemetry card displaying current temperature, humidity, rain rate, ET0, centroid coordinates, and an on-demand refresh button.
- **`DataSourcesView`:** Open-Meteo registered with complete metadata, spatial resolution, and limitations.
- **`SystemMonitoringView`:** Integrated 5th pipeline item tracking forecast telemetry status.

---

## 4. Verification & Test Evidence

### 4.1 Backend Test Results
The backend test suite was executed using pytest, covering all existing regression tests and 17 dedicated Phase 3A tests:
- **Command:** `PYTHONPATH=backend backend/venv/bin/pytest backend/tests`
- **Result:** `204 passed, 1 warning in 5.22s`
- **Test Categories:**
  - Metadata verification and CC-BY 4.0 licensing attribution.
  - Centroid coordinate resolution for Gorakhpur, Mahoba, Patna, Lucknow, Varanasi, Gaya.
  - Hourly validation, zero vs missing null semantics, physical bounds clamping and error rejection.
  - Hourly-to-daily aggregation with 20/24 valid hours threshold.
  - Cache hit, TTL expiration, stale fallback (3h–24h), and pending fallback (>24h).
  - Concurrency deduplication across concurrent async requests.
  - Endpoint contracts (`GET /live`, `GET /status`, `POST /refresh`) under both `LIVE_DATA_ENABLED=False` and `True`.
  - Ingestion and risk engine evaluation in `mode="live"`.

### 4.2 Frontend Test Results
The frontend test suite was executed using Vitest:
- **Command:** `npm test -- --run`
- **Result:** `10 test files passed, 44 tests passed in 2.40s`
- **Test Categories:**
  - `DataProvenanceBadge` rendering for `LIVE_MODEL`, `PROVIDER_ERROR`, and `FORECAST`.
  - `DataSourcesView` displaying Open-Meteo attribution and representative-point disclaimers.
  - Multi-district isolation, district selector, upload workflow, and E2E resilience.

### 4.3 Production Build Verification
- **Command:** `npm run build` (`tsc && vite build`)
- **Result:** Exit code `0` in `1.31s`. Zero TypeScript or bundler errors.

---

## 5. Free-Tier & Zero-Cost Compliance Summary

| Constraint | Architectural Strategy | Compliance Verification |
|---|---|---|
| **Monthly Cost** | ₹0 / $0 | Free public Open-Meteo Forecast API; no paid subscriptions or keys required. |
| **Database Storage** | ₹0 SQLite / memory | Persistent disk cache stored locally in `backend/data/cache/environmental_forecast_cache.json`. No PostgreSQL disk add-ons required. |
| **Worker Daemons** | None | Request-triggered lazy caching. Zero background scheduler processes, Celery workers, or continuous loops. |
| **Memory Limit** | 512 MB Render Free Tier | Lightweight in-memory cache with atomic file serialization; bounded JSON payload (~15 KB per district). |
| **Rate Limit Protection** | 10,000 req/day API limit | 3-hour TTL per district ensures max 8 requests/district/day under normal usage. Concurrency lock eliminates duplicate parallel calls. |
