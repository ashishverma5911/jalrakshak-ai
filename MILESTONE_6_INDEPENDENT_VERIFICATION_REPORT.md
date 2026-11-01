# JALRAKSHAK AI — MILESTONE 6 INDEPENDENT VERIFICATION REPORT
## Objective Scientific Audit of Real-World Data Integration, GPM/CHIRPS Ingestion, SRTM Elevation Benchmarks, Spatial Aggregation, and Risk Engine Couplings

**Audit Execution Date:** October 31, 2026  
**Auditor Role:** Independent Lead Geospatial, Data & Software Systems Auditor  
**Repository Working Directory:** `/Users/ashish/Downloads/JalRakshak A.I.`  
**Current Git Branch:** `feature/milestone-2-data-ingestion-ui`  
**Git Integrity Status:** Clean feature branch; zero commits, zero pushes, zero branch switching, zero deployments to Vercel/Render. External repositories (HVAC, TravelMate, Language Exchange, TM) untouched.  
**Audit Method:** Direct file inspection, static AST tracing, empirical recalculations from raw stored records, and live API test-client executions.

---

## EXECUTIVE AUDIT SUMMARY & SCORECARD

| Audit Verification Item | Required Evaluation | Independent Audit Outcome | Verification Status |
|---|---|---|---|
| **1. CHIRPS Observational Records** | Verify CSV records against original downloaded UCSB CHIRPS source files. | Records were fetched via Open-Meteo Historical API proxy (`lat/lon` query) rather than raw UCSB CHIRPS NetCDF/GeoTIFF raster tiles. No raw UCSB source files exist in the repository. | **FAIL / NOT VERIFIED AGAINST RAW UCSB SOURCES** |
| **2. NASA GPM IMERG Late Run Data** | Verify whether genuine GPM Late Run data was downloaded, stored, and integrated into risk engines. | No GPM IMERG data files (HDF5/NetCDF/CSV) exist. `GPMIMERGPipeline` exists only as a standalone schema definition and is **NEVER** imported or called by `flood_engine.py` or `drought_engine.py`. | **NOT INTEGRATED** |
| **3. NASA SRTM Elevation & 2.7m Std Dev** | Recalculate SRTM elevation statistics across complete district boundaries; investigate Gorakhpur 2.7m std dev. | Geomorphologically verified: Gorakhpur's Terai plain is exceptionally flat (slope 0.15–0.35 m/km). Recalculation across N=100 polygon points yields mean 78.60m, std 2.61m. However, reported pipeline numbers were sampled from only 30 points via API; no offline SRTM raster DEM exists. | **VERIFIED WITH METHODOLOGICAL CAVEATS** |
| **4. Administrative Boundaries & Spatial Aggregation** | Validate district GeoJSON geometry and area-weighted spatial aggregation execution. | Boundaries are valid polygons/multipolygons matching official borders. However, `SpatialAggregator.aggregate_gridded_precipitation` is only called in unit tests; runtime API ingestion loads pre-existing scalar CSVs without runtime spatial aggregation. | **PARTIAL PASS / OFFLINE ONLY** |
| **5. Independent Indicator Recalculation** | Recalculate flood and drought indicators directly from stored observation CSVs. | Mathematical calculations in `FloodRiskEngine` and `DroughtRiskEngine` exactly match manual recalculations from stored CSVs. Verified mode accurately computes 0.0 mm 7-day Gorakhpur rainfall and 719.7 mm Mahoba 90-day rainfall. | **PASS** |
| **6. AI Assistant Engine Coupling** | Trace whether AI Assistant genuinely uses actual risk-engine outputs. | Assistant retrieves engine objects, but suffers from two severe defects: (1) Python falsy-zero bug (`0.0 or 286.0`) forces verified 0.0mm rainfall to revert to 286.0mm demo constant; (2) Keyword hijack bug redirects candidate queries to Gorakhpur/Mahoba. | **FAIL** |
| **7. Candidate District Isolation** | Verify candidate districts (Lucknow, Patna, Gaya, Varanasi) cannot inherit pilot data. | Dashboard overview and direct risk endpoints strictly isolate candidate districts (return `DATA_PENDING`, `0.0` values, and 400 rejection). However, AI Assistant leaks pilot answers when candidate queries contain words "flood" or "drought". | **PARTIAL PASS / DEFECT IN ASSISTANT** |

---

## DETAILED VERIFICATION FINDINGS

```
========================================================================================
CHECK 1: CHIRPS CSV RECORDS AUDIT AGAINST ORIGINAL DOWNLOADED SOURCES
========================================================================================
```

### 1.1. Inspection of Repository Files
- Target Files Inspected:
  - `backend/data/gorakhpur_chirps_daily_verified.csv` (4,320 lines, 4,319 records)
  - `backend/data/mahoba_chirps_daily_verified.csv` (4,320 lines, 4,319 records)
  - `backend/data/gorakhpur_chirps_daily.csv` (4,320 lines, 4,319 records)
  - `backend/data/mahoba_chirps_daily.csv` (4,320 lines, 4,319 records)
  - `backend/data/climatological_normals_1991_2020.json` (72 lines)
  - `backend/data/generate_baseline_data.py` (97 lines)

### 1.2. Provenance Trace & Extraction Audit
A search for downloaded raw raster tiles from the University of California, Santa Barbara (UCSB) Climate Hazards Center (`ftp://ftp.chc.ucsb.edu/products/CHIRPS-2.0/` or `https://data.chc.ucsb.edu/products/CHIRPS/v2.0/`):
```bash
find backend -iname "*.nc*" -o -iname "*.tif*" -o -iname "*.gz"
# Result: 0 files found.
```
Inspection of task trajectory log `transcript_full.jsonl` (line 1864, task id `task-1873`) revealed the actual generation script:
```python
# Actual extraction command recorded in system log:
url = f'https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lng}&start_date=2015-01-01&end_date=2026-10-28&daily=precipitation_sum&timezone=auto'
# Followed by CSV creation:
# 'data_source': 'chirps_v2.0_daily_station_blend'
```

### 1.3. Audit Findings & Reality Assessment
1. **Source Mismatch**: The 4,319 daily records stored in `gorakhpur_chirps_daily_verified.csv` and `mahoba_chirps_daily_verified.csv` were **NOT** extracted from raw UCSB CHIRPS NetCDF/GeoTIFF raster tiles. They were downloaded via the Open-Meteo Historical Weather Archive REST API for two discrete point centroids (`(26.7606, 83.3732)` and `(25.2926, 79.8722)`).
2. **Arbitrary Attribution**: The script applied the label `chirps_v2.0_daily_station_blend` to the CSV rows, despite Open-Meteo archive using blended ERA5-Land reanalysis / ECMWF models with regional station blending.
3. **Absence of Raw Gridded Archive**: There are zero raw spatial raster files stored in the repository.

**Status: FAIL / NOT VERIFIED AGAINST RAW UCSB CHIRPS SOURCES**

---

```
========================================================================================
CHECK 2: NASA GPM IMERG LATE RUN DATA DOWNLOAD & ENGINE INTEGRATION AUDIT
========================================================================================
```

### 2.1. File Storage Audit
Search command:
```bash
find backend -iname "*gpm*" -o -iname "*imerg*" -o -iname "*.h5" -o -iname "*.hdf*"
```
Output:
```
backend/app/pipeline/gpm_pipeline.py
```
No raw HDF5 files (`3B-DAY-L.MS.MRG.3IMERG.*.HDF5`), NetCDF files, or extracted GPM CSV files exist in `backend/data/` or anywhere in the workspace.

### 2.2. Engine Integration Trace
Static code audit of `backend/app/engine/flood_engine.py` and `backend/app/engine/drought_engine.py`:
- `grep -rn "GPMIMERGPipeline" backend/app/engine/` -> **0 occurrences**.
- `grep -rn "gpm" backend/app/engine/` ->
  - `backend/app/engine/flood_engine.py:226`: Static metadata string: `source_name="NASA GPM IMERG Late Run"`.
  - `backend/app/engine/assistant_engine.py:242, 271`: Text citations in assistant prompts.

### 2.3. Audit Findings
`GPMIMERGPipeline` in `backend/app/pipeline/gpm_pipeline.py` contains class definitions and record validation logic (`validate_gpm_record`), but it is an isolated stub. It is **never instantiated, called, or referenced by `DataIngestionService`, `FloodRiskEngine`, or `DroughtRiskEngine`**.

**Status: NOT INTEGRATED (Explicitly Confirmed)**

---

```
========================================================================================
CHECK 3: NASA SRTM ELEVATION STATISTICS & GORAKHPUR 2.7m STD DEV INVESTIGATION
========================================================================================
```

### 3.1. Reported Baseline in Code
`backend/app/pipeline/srtm_pipeline.py` defines:
```python
"district-gorakhpur": {
    "mean_elevation_m": 77.7,
    "min_elevation_m": 73.0,
    "max_elevation_m": 83.0,
    "elevation_std_m": 2.7,
    "slope_degrees_avg": 0.35,
    "terrain_vulnerability_index": 0.88,
}
"district-mahoba": {
    "mean_elevation_m": 197.1,
    "min_elevation_m": 145.0,
    "max_elevation_m": 246.0,
    "elevation_std_m": 29.9,
    "slope_degrees_avg": 2.85,
    "terrain_vulnerability_index": 0.15,
}
```

### 3.2. Forensic Origin of the 2.7m Standard Deviation
Inspection of step 1864 in `transcript_full.jsonl` shows how these numbers were generated:
```python
# Script generated a 10x10 bounding grid, filtered by poly.contains(p), and took only:
valid_points[:30]
# Then called:
url = f'https://api.open-meteo.com/v1/elevation?latitude={lat_str}&longitude={lon_str}'
```
The reported statistics were calculated from **only 30 points** across Gorakhpur's $3,323.7 \text{ km}^2$ land area (~1 point per $110 \text{ km}^2$).

### 3.3. Independent Recalculation Across Denser Boundary Polygons
To independently verify whether a 2.7m standard deviation is physically realistic or an artifact of sparse sampling, an independent test script sampled a dense regular grid of internal polygon points ($N=100$ for Gorakhpur, $N=60$ for Mahoba):

| Terrain Metric | Gorakhpur Reported | Gorakhpur Independent Recalculation ($N=100$) | Mahoba Reported | Mahoba Independent Recalculation ($N=60$) |
|---|---|---|---|---|
| **Mean Elevation** | 77.7 m | **78.60 m** | 197.1 m | **196.85 m** |
| **Elevation Std Dev ($\sigma$)** | 2.7 m | **2.61 m** | 29.9 m | **24.81 m** |
| **Minimum Elevation** | 73.0 m | **71.00 m** | 145.0 m | **159.00 m** |
| **Maximum Elevation** | 83.0 m | **87.00 m** | 246.0 m | **258.00 m** |
| **Elevation Relief Range** | 10.0 m | **16.00 m** | 101.0 m | **99.00 m** |

### 3.4. Scientific Geomorphological Explanation for Low Standard Deviation
1. **Geological Context**: Gorakhpur is situated entirely within the Indo-Gangetic alluvium of the middle Terai foreland basin. The underlying sediment consists of deep, unconsolidated Quaternary sand, silt, and clay laid down by the trans-Himalayan Rapti, Rohini, and Ghaghara river systems.
2. **Hydraulic Gradient**: The regional slope from north to south averages only $0.15\text{ to }0.30\text{ m/km}$. Across the 100 km latitudinal extent of the district boundary ($26.22^\circ\text{N to }27.12^\circ\text{N}$), elevation only decreases from ~87 m MSL at the Nepal/Maharajganj frontier to ~71 m MSL at the Barhaj/Ghaghara confluence.
3. **Absence of Relief Features**: There are zero bedrock outcrops, hills, or escarpments. Consequently, an elevation standard deviation of **$2.6\text{ to }2.7\text{ m}$ is physically genuine and accurate for this specific landform**, explaining its high waterlogging and drainage congestion vulnerability.
4. **Audit Caveat**: While geomorphologically valid, the values in `srtm_pipeline.py` remain a static 30-point API sample rather than an offline 1-arc-second (~30 m) continuous raster DEM calculation.

**Status: VERIFIED WITH METHODOLOGICAL CAVEATS**

---

```
========================================================================================
CHECK 4: ADMINISTRATIVE BOUNDARIES, GEOMETRY & SPATIAL AGGREGATION AUDIT
========================================================================================
```

### 4.1. Boundary File Integrity Verification
- `backend/data/boundaries/district-gorakhpur.geojson`:
  - Geometry: `Polygon` (Single contiguous boundary)
  - Topological Validity: `geom.is_valid == True`
  - Bounding Box: `[83.0677616, 26.2187521, 83.6710430, 27.1170764]`
  - Area: $0.301873 \text{ deg}^2 \approx 3,323.7 \text{ km}^2$ (Official census area: $3,321 \text{ km}^2$; discrepancy $< 0.1\%$).
- `backend/data/boundaries/district-mahoba.geojson`:
  - Geometry: `MultiPolygon` (Accounted for administrative enclave parcels)
  - Topological Validity: `geom.is_valid == True`
  - Bounding Box: `[79.2789533, 25.0320840, 80.2266939, 25.6432450]`
  - Area: $0.290031 \text{ deg}^2 \approx 3,229.7 \text{ km}^2$ (Official census area: $3,116 \text{ km}^2$).

### 4.2. Spatial Aggregation Execution Trace
In `backend/app/pipeline/spatial_aggregation.py`:
- `SpatialAggregator.generate_grid_cells_for_bounds`: Generates $0.05^\circ$ grid cells.
- `SpatialAggregator.aggregate_gridded_precipitation`: Performs area-weighted polygon intersection $\sum (P_i \cdot A_i) / \sum A_i$.
- Unit test in `backend/tests/test_milestone6_real_data.py`: `test_spatial_aggregation_with_boundary_intersection` PASSED.

### 4.3. Runtime Pipeline Audit
Inspection of `backend/app/pipeline/ingestion.py` (lines 66–74):
```python
if mode == "verified":
    csv_path = verified_path if verified_path.exists() else demo_path
    # For verified operational mode, validate administrative boundary polygon
    SpatialAggregator.load_district_boundary(region_id)
else:
    csv_path = demo_path if demo_path.exists() else verified_path
```
**CRITICAL FINDING**: `SpatialAggregator.load_district_boundary` is called **only as an existence gate**. The engine loads a pre-computed scalar CSV (`gorakhpur_chirps_daily_verified.csv`) and never executes `SpatialAggregator.aggregate_gridded_precipitation` on operational requests. Real-time gridded area-weighting exists only as an offline library module.

**Status: PARTIAL PASS / OFFLINE ONLY**

---

```
========================================================================================
CHECK 5: INDEPENDENT RECALCULATION OF RISK ENGINE INDICATORS FROM STORED DATA
========================================================================================
```

### 5.1. Method
Executed independent script importing Pandas, NumPy, and SciPy directly, loading `gorakhpur_chirps_daily_verified.csv` and `mahoba_chirps_daily_verified.csv` without calling engine wrapper methods. Evaluated anchor date: `2026-10-28`.

### 5.2. Gorakhpur Flood Indicators Comparison

| Indicator | Mathematical Definition | Raw CSV Manual Recalculation | `FloodRiskEngine` Output | Audit Match |
|---|---|---|---|---|
| `flood_precip_7d_accum` | $\sum_{t=22}^{28} P_t$ | **0.0 mm** (dry spell: 7 consecutive 0.0s) | **0.0 mm** | **EXACT MATCH** |
| `flood_precip_7d_anomaly` | $(P_{7d} - N_{7d}) / N_{7d}$ | $(0.0 - 9.08) / 9.08 = \mathbf{-100.0\%}$ | **-100.0%** | **EXACT MATCH** |
| `flood_precip_30d_accum` | $\sum_{t=29\text{ Sep}}^{28\text{ Oct}} P_t$ | **16.8 mm** | **16.8 mm** | **EXACT MATCH** |
| `flood_heavy_rainfall_days`| $\text{Count}(P_t \ge 64.5)$ | **0.0 days** | **0.0 days** | **EXACT MATCH** |
| `flood_terrain_vulnerability`| Inverted logistic DEM | **0.88** | **0.88** | **EXACT MATCH** |
| `flood_historical_percentile`| Empirical CDF of 7d sums | **0.0 percentile** | **0.0 percentile** | **EXACT MATCH** |

*Note on Ground Truth vs Demo*: In the prototype demonstration mode, Gorakhpur 7-day rainfall was mocked at `286.0 mm` (+65% anomaly) to display an active flood state. Under the verified observational file (`gorakhpur_chirps_daily_verified.csv`), late October 2026 was completely dry (0.0 mm), resulting in a calculated risk level of **LOW**, not HIGH.

### 5.3. Mahoba Drought Indicators Comparison

| Indicator | Mathematical Definition | Raw CSV Manual Recalculation | `DroughtRiskEngine` Output | Audit Match |
|---|---|---|---|---|
| `drought_precip_90d_accum` | $\sum_{t=31\text{ Jul}}^{28\text{ Oct}} P_t$ | **719.7 mm** | **719.7 mm** | **EXACT MATCH** |
| `drought_precip_90d_anomaly`| Departure from $453.6\text{mm}$ normal | $(719.7 - 453.6) / 453.6 = \mathbf{+58.7\%}$ | **+58.7%** | **EXACT MATCH** |
| `drought_seasonal_deficit` | Kharif (Jun–Sep) vs $845.4\text{mm}$ | $(943.3 - 845.4) / 845.4 = \mathbf{+11.6\%}$ | **+11.6%** | **EXACT MATCH** |
| `drought_spi_3` | 2-parameter Gamma MLE Z-score | $Z = \mathbf{+1.31}$ (Moderately Wet) | **+1.31** | **EXACT MATCH** |
| `drought_consecutive_dry_days`| Max run of $P_t < 1.0$ (60d window)| **32 days** (27 Sep – 28 Oct) | **32.0 days** | **EXACT MATCH** |
| `drought_dry_day_frequency` | Days $< 2.5\text{mm} / 91\text{ days}$ | $51 / 91 = \mathbf{56.0\%}$ | **56.0%** | **EXACT MATCH** |

*Note on Ground Truth vs Demo*: In demonstration mode, Mahoba was mocked as a severe agricultural drought (-72% Kharif deficit, SPI-3 = -1.84). The verified observations indicate that 2026 experienced an above-average monsoon (943.3 mm), followed by a dry October (32 consecutive dry days), which the mathematical engine accurately captured as a positive SPI-3 (+1.31) with high recent dry-spell frequency.

**Status: PASS (100% mathematical fidelity on stored records)**

---

```
========================================================================================
CHECK 6: AI ASSISTANT COUPLING & REASONING PIPELINE AUDIT
========================================================================================
```

### 6.1. Architectural Flow Trace
The execution path of `GroundedAssistantEngine` (`backend/app/engine/assistant_engine.py`):
1. User prompt enters `process_chat(query, location)`.
2. Input is passed to `retrieve_grounded_evidence(location, query, mode)`.
3. If neural runtime is offline, calls `synthesize_transparent_grounded_answer(clean_query, grounded_data)`.

### 6.2. CRITICAL DEFECT #1: Falsy-Zero Fallback Corruption
In `backend/app/engine/assistant_engine.py` (lines 262–266):
```python
if loc == "gorakhpur":
    rain_7d = indicators.get("flood_precip_7d_accum") or indicators.get("gorakhpur_rain_7d", 286.0)
    anomaly_7d = indicators.get("flood_precip_7d_anomaly") or indicators.get("gorakhpur_anomaly_7d", 65.3)
    rain_30d = indicators.get("flood_precip_30d_accum") or indicators.get("gorakhpur_rain_30d", 512.0)
    percentile = indicators.get("flood_historical_percentile") or indicators.get("gorakhpur_percentile_7d", 94.2)
```
**The Bug**: In Python, `0.0` is falsy (`bool(0.0) == False`). When the verified risk engine correctly outputs `flood_precip_7d_accum = 0.0`:
`0.0 or 286.0` evaluates to **`286.0`**!  
Similarly, `flood_historical_percentile = 0.0` evaluates to **`94.2`**!  
However, `flood_precip_7d_anomaly = -100.0` is truthy, so it remains `-100.0`.

**The Corrupted Output**: The AI Assistant outputs the following contradictory nonsense to users:
> *"7-Day Cumulative Rainfall: 286.0 mm, representing a departure of -100.0% from the 30-year climatological normal... Current 7-day accumulation ranks at the 94.2th percentile historically."*

### 6.3. CRITICAL DEFECT #2: Keyword-Based District Hijacking
In `backend/app/engine/assistant_engine.py` (lines 88–93):
```python
# Auto-detect location context from query keywords if generic
if "mahoba" in q_lower or "drought" in q_lower or "bundelkhand" in q_lower:
    target_loc = "mahoba"
elif "gorakhpur" in q_lower or "flood" in q_lower or "rapti" in q_lower:
    target_loc = "gorakhpur"
```
**The Bug**: If a user selects a candidate district like Lucknow and asks: `"What is the flood risk in Lucknow?"`:
Because `q_lower` contains `"flood"`, lines 91–92 **unconditionally override `target_loc` from `"lucknow"` to `"gorakhpur"`**, bypassing the candidate isolation check!

**Status: FAIL (Severe falsy-zero corruption and query hijacking confirmed)**

---

```
========================================================================================
CHECK 7: CANDIDATE DISTRICT DATA ISOLATION & ZERO-BLEED VERIFICATION
========================================================================================
```

Tested candidates: `lucknow`, `patna`, `gaya`, `varanasi`.

### 7.1. Dashboard Overview Isolation Audit (`GET /api/v1/dashboard?location={id}`)
- `data_mode`: `"DATA_PENDING"` (Verified)
- `data_freshness_status`: `"pending_onboarding"` (Verified)
- `is_demo_data`: `False` (Verified)
- All 4 metric cards:
  - `title`: "Current Rainfall", "7-Day Cumulative", "Seasonal Baseline", "Hazard Index"
  - `value`: `0.0` (Zero leak confirmed)
  - `hazard_type`: `"pending"` (Zero leak confirmed)
  - `context_note`: Explicitly warns *"Telemetry pipeline offline; zero data bleed enforced"*.
- **Dashboard Isolation Status: PASS**

### 7.2. Direct Risk Endpoints Audit
- `GET /api/v1/risk/flood?location=lucknow&mode=verified`: Returns **`HTTP 400 Bad Request`** with `Validated administrative polygon unavailable for 'district-lucknow'`.
- `GET /api/v1/risk/drought?location=patna&mode=verified`: Returns **`HTTP 400 Bad Request`**.
- Refuses to interpolate or substitute Gorakhpur/Mahoba values.
- **Direct API Isolation Status: PASS**

### 7.3. AI Assistant Isolation Audit
- Query: `{"query": "What is the status of lucknow?", "location": "lucknow"}`:
  - Correctly outputs: `DATA_PENDING` with statement: *"Candidate district 'Lucknow' is unlinked from active telemetry. Zero cross-district data bleed is strictly enforced."* (PASS)
- Query: `{"query": "What is the flood risk in lucknow?", "location": "lucknow"}`:
  - **LEAKAGE**: Due to Defect #2 (Keyword Hijack), returns Gorakhpur flood data under a Lucknow query!
- **Assistant Isolation Status: FAIL**

**Status: PARTIAL PASS / CONDITIONAL LEAKAGE IN ASSISTANT**

---

## CONCRETE AUDIT EVIDENCE SUMMARY TABLE

| Investigation Target | Evidence Location | Discovered Reality | Verdict |
|---|---|---|---|
| **Raw CHIRPS Archive** | `backend/data/` | No raw NetCDF/GeoTIFF raster tiles exist. Data was pulled from Open-Meteo single-point archive API. | **FAIL** |
| **GPM IMERG Integration** | `backend/app/pipeline/gpm_pipeline.py` | Pipeline is a disconnected stub; never imported or called in risk calculations. | **NOT INTEGRATED** |
| **SRTM Topography** | `backend/app/pipeline/srtm_pipeline.py` | 2.7m std dev for Gorakhpur is physically authentic for Terai alluvium, but sampled from only 30 points via API. | **CAVEAT** |
| **Geospatial Boundaries** | `backend/data/boundaries/*.geojson` | Boundaries are valid polygons (~3,323 km² and ~3,229 km²). | **PASS** |
| **Runtime Spatial Aggregation** | `backend/app/pipeline/spatial_aggregation.py` | Area-weighted polygon aggregation exists as test-only module; runtime loads static CSVs. | **OFFLINE ONLY** |
| **Risk Engine Indicators** | `backend/app/engine/*_engine.py` | 100% mathematical match between stored observations and engine indicators. | **PASS** |
| **AI Assistant Grounding** | `backend/app/engine/assistant_engine.py` | Falsy zero bug converts 0.0mm rainfall to 286.0mm; keyword hijack leaks Gorakhpur data into Lucknow queries. | **FAIL** |
| **Candidate District Isolation** | `backend/app/api/dashboard.py` | Dashboard & Risk APIs strictly isolate candidates with 0.0 values and 400 errors. | **PASS** |

---

## CONCLUSION & AUDIT VERDICT

1. **Mathematical engines are verified**: When supplied with tabular daily observations, `FloodRiskEngine` and `DroughtRiskEngine` compute antecedent accumulations, climatological departures, and SPI-3 with mathematical accuracy.
2. **Boundary polygons are verified**: Administrative polygons for Gorakhpur and Mahoba are topologically valid and geospatially accurate.
3. **Data provenance is ungrounded**: The claim of genuine UCSB CHIRPS and NASA GPM IMERG Late Run gridded satellite pipelines is inaccurate. GPM IMERG is **NOT INTEGRATED**, and CHIRPS was populated via an external point-location Open-Meteo API.
4. **AI Assistant contains critical software defects**: Python `0.0 or fallback` logic corrupts verified zero-rainfall reporting, and keyword overrides cause candidate district queries to leak pilot responses.

**FINAL AUDIT STATUS: INDEPENDENT VERIFICATION COMPLETE. CRITICAL GAPS AND DEFECTS FORMALLY DOCUMENTED.**  
*Awaiting user approval before any code modifications.*
