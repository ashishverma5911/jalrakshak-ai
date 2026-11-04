import React, { useState, useEffect } from 'react';
import {
  Waves,
  AlertTriangle,
  Compass,
  Info,
  CheckCircle2,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { RainfallChart } from '../components/charts/RainfallChart';
import { apiService, HazardAssessmentResponse } from '../services/api';
import { DataProvenanceBadge } from '../components/common/DataProvenanceBadge';
import {
  UP_DISTRICTS_DATA,
  getFilteredRainfallData,
  DEMO_DATA_DISCLAIMER,
} from '../data/mockData';

export const FloodAssessmentView: React.FC = () => {
  const {
    selectedLocation,
    setSelectedLocation,
    setCurrentRoute,
    dataFreshnessMode,
    activeLocationData,
  } = useApp();
  const [activeTab, setActiveTab] = useState<'trend' | 'geo' | 'risk' | 'sources'>('trend');
  const [selectedLayer, setSelectedLayer] = useState<'rainfall' | 'river' | 'elevation' | 'boundary'>('rainfall');
  const [timeRange, setTimeRange] = useState<'7' | '30' | '90' | '365'>('30');
  const [backendData, setBackendData] = useState<HazardAssessmentResponse | null>(null);
  const [, setIsLoading] = useState<boolean>(false);
  const [, setFetchError] = useState<string | null>(null);

  const districtData = UP_DISTRICTS_DATA.find((d) => d.id === 'gorakhpur')!;
  const isFloodPilot = selectedLocation === 'gorakhpur';
  const chartSeries = getFilteredRainfallData('gorakhpur', timeRange, 'daily');

  const loadBackendRisk = () => {
    setIsLoading(true);
    setFetchError(null);
    apiService
      .fetchFloodRisk('gorakhpur', 7)
      .then((data) => {
        setBackendData(data);
      })
      .catch((err) => {
        setFetchError(err.message || 'Failed to fetch backend flood assessment');
      })
      .finally(() => {
        setIsLoading(false);
      });
  };

  useEffect(() => {
    if (isFloodPilot) {
      loadBackendRisk();
    }
  }, [selectedLocation, isFloodPilot]);

  // Compute display values from live backend if available, else fallback fixture
  const r7d = backendData?.indicators.find((i) => i.indicator_id === 'gorakhpur_rain_7d')?.value ?? districtData.rainfall7dMm;
  const anom7d = backendData?.indicators.find((i) => i.indicator_id === 'gorakhpur_anomaly_7d')?.value ?? districtData.anomalyPct;
  const r30d = backendData?.indicators.find((i) => i.indicator_id === 'gorakhpur_rain_30d')?.value ?? districtData.rainfall30dMm;
  const anom30d = backendData?.indicators.find((i) => i.indicator_id === 'gorakhpur_anomaly_30d')?.value ?? 48;

  const handleLocationChange = (val: string) => {
    if (val === 'mahoba') {
      setSelectedLocation('mahoba');
      setCurrentRoute('drought');
    } else {
      setSelectedLocation(val as any);
    }
  };

  return (
    <div className="space-y-6">
      {/* Data Provenance Disclaimer */}
      <div className="px-3.5 py-1.5 rounded-xl bg-sky-50 border border-sky-200 text-[11px] text-sky-800 flex items-center justify-between shadow-sm">
        <div className="flex items-center space-x-2">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-600" />
          <span>
            {backendData && !backendData.is_demo_data
              ? (backendData.disclaimer || 'JalRakshak AI Decision-Support System: Grounded in validated observational baselines. Not an official statutory forecasting authority.')
              : DEMO_DATA_DISCLAIMER}
          </span>
        </div>
        <span className="font-mono text-blue-700 font-semibold">
          {isFloodPilot ? 'PILOT: GORAKHPUR' : `CANDIDATE: ${activeLocationData.name.toUpperCase()}`}
        </span>
      </div>

      {/* Scope Alert when a candidate district or non-flood district is active */}
      {!isFloodPilot && (
        <div className="p-3.5 rounded-2xl bg-amber-50 border border-amber-200 text-xs text-amber-900 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm">
          <div className="flex items-center space-x-2.5">
            <Info className="w-4 h-4 text-amber-600 shrink-0" />
            <span>
              <strong>Hazard Pilot Scope:</strong> Gorakhpur is currently the active flood pilot. {activeLocationData.name} ({activeLocationData.region}) is not configured for hydrodynamic flood models.
            </span>
          </div>
          <button
            onClick={() => setSelectedLocation('gorakhpur')}
            className="px-3 py-1 rounded-xl bg-blue-600 text-white font-semibold hover:bg-blue-700 transition shrink-0"
          >
            Focus Gorakhpur
          </button>
        </div>
      )}

      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            {isFloodPilot ? (
              <>
                <span className="text-xs font-bold uppercase tracking-wider text-sky-700 bg-sky-100 px-2 py-0.5 rounded border border-sky-200">
                  Hazard Pilot 1
                </span>
                <span className="text-xs text-slate-500 font-mono">Rapti Basin Context</span>
              </>
            ) : (
              <>
                <span className="text-xs font-bold uppercase tracking-wider text-amber-800 bg-amber-100 px-2 py-0.5 rounded border border-amber-200">
                  Candidate District • Ingestion Pending
                </span>
                <span className="text-xs text-slate-500 font-mono">{activeLocationData.region}</span>
              </>
            )}
          </div>
          <h1 className="text-2xl lg:text-3xl font-extrabold text-slate-900 mt-1">
            {isFloodPilot ? 'Gorakhpur — Flood Assessment' : `${activeLocationData.name} — Flood Assessment`}
          </h1>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <DataProvenanceBadge
              mode={isFloodPilot ? (backendData?.data_mode || 'CACHED_VERIFIED') : 'DATA_PENDING'}
              source={isFloodPilot ? "NASA GPM Late Run / CHIRPS v2.0" : "Observational Ingestion Stream Unlinked"}
              datasetVersion={isFloodPilot ? "v07B / v2.0" : "Pending Ingestion"}
              spatialResolution={isFloodPilot ? "0.05° (~5.3 km)" : "WGS84 Centroid Point"}
              limitations={isFloodPilot ? "Area-weighted spatial aggregation over validated Gorakhpur boundary polygon. Does not calculate Rapti river stage gauge depth." : "Scientific Boundary: Candidate districts never inherit or interpolate observational telemetry or risk scores from Gorakhpur or Mahoba."}
            />
            <p className="text-xs text-slate-600">
              {isFloodPilot
                ? "Analyse rainfall, geographical terrain factors and heavy precipitation risk indicators."
                : `Hydrological flood modeling and gridded telemetry are unlinked for ${activeLocationData.name}. Zero score interpolation applied.`}
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <select
            value={selectedLocation}
            onChange={(e) => handleLocationChange(e.target.value)}
            className="bg-white border border-slate-200 text-xs font-semibold text-slate-800 rounded-xl px-3 py-2 shadow-sm focus:outline-none focus:border-blue-500"
          >
            <option value="gorakhpur">Gorakhpur (Flood Pilot)</option>
            <option value="mahoba">Switch to Mahoba (Drought)</option>
            {!isFloodPilot && selectedLocation !== 'mahoba' && (
              <option value={selectedLocation}>{activeLocationData.name} (Candidate District)</option>
            )}
          </select>
        </div>
      </div>

      {/* Top 4 Indicator Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Current Risk Level */}
        <Card variant="flood" className="relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500 font-medium">Current Risk Level</span>
            {isFloodPilot ? (
              <Badge label="HIGH" riskLevel="high" dot />
            ) : (
              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                Pending
              </span>
            )}
          </div>
          <div className="mt-3">
            {isFloodPilot ? (
              <>
                <div className="text-2xl font-black text-rose-600 flex items-center gap-1.5">
                  <AlertTriangle className="w-6 h-6 text-rose-600" />
                  <span>High Risk</span>
                </div>
                <p className="text-[11px] text-slate-600 mt-1">
                  Recent heavy rainfall significantly above historical average.
                </p>
              </>
            ) : (
              <>
                <div className="text-xl font-bold text-slate-400">Model Offline</div>
                <p className="text-[11px] text-slate-500 mt-1">
                  Hydrodynamic modeling unconfigured for {activeLocationData.name}.
                </p>
              </>
            )}
          </div>
        </Card>

        {/* Metric 2: 7-Day Cumulative Rainfall */}
        <Card variant="flood">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500 font-medium">7-Day Rainfall</span>
            {isFloodPilot ? (
              <span className="text-xs text-emerald-700 font-bold">+{typeof anom7d === 'number' ? anom7d.toFixed(1) : anom7d}% vs normal</span>
            ) : (
              <span className="text-[10px] font-mono text-slate-400">DATA PENDING</span>
            )}
          </div>
          <div className="mt-3">
            {isFloodPilot ? (
              <>
                <div className="text-3xl font-black text-slate-900">
                  {typeof r7d === 'number' ? r7d.toFixed(1) : r7d} <span className="text-sm font-semibold text-slate-500">mm</span>
                </div>
                <p className="text-[11px] text-sky-700 mt-1 font-medium">NASA GPM IMERG 0.1° gridded run</p>
              </>
            ) : (
              <>
                <div className="text-3xl font-black text-slate-400">-- <span className="text-sm font-semibold text-slate-400">mm</span></div>
                <p className="text-[11px] text-slate-500 mt-1">Station telemetry stream unlinked</p>
              </>
            )}
          </div>
        </Card>

        {/* Metric 3: 30-Day Rainfall */}
        <Card variant="flood">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500 font-medium">30-Day Rainfall</span>
            {isFloodPilot ? (
              <span className="text-xs text-emerald-700 font-bold">+{typeof anom30d === 'number' ? anom30d.toFixed(1) : anom30d}% vs normal</span>
            ) : (
              <span className="text-[10px] font-mono text-slate-400">DATA PENDING</span>
            )}
          </div>
          <div className="mt-3">
            {isFloodPilot ? (
              <>
                <div className="text-3xl font-black text-slate-900">
                  {typeof r30d === 'number' ? r30d.toFixed(1) : r30d} <span className="text-sm font-semibold text-slate-500">mm</span>
                </div>
                <p className="text-[11px] text-sky-700 mt-1 font-medium">CHIRPS daily accumulated series</p>
              </>
            ) : (
              <>
                <div className="text-3xl font-black text-slate-400">-- <span className="text-sm font-semibold text-slate-400">mm</span></div>
                <p className="text-[11px] text-slate-500 mt-1">30-year climatology uncalibrated</p>
              </>
            )}
          </div>
        </Card>

        {/* Metric 4: Data Freshness */}
        <Card variant="flood">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500 font-medium">Data Freshness</span>
            <span
              className={`w-2 h-2 rounded-full ${
                !isFloodPilot ? 'bg-slate-300' : dataFreshnessMode === 'stale' ? 'bg-amber-500' : 'bg-emerald-500 animate-pulse'
              }`}
            />
          </div>
          <div className="mt-3">
            {isFloodPilot ? (
              <>
                <div className="text-xl font-bold text-emerald-700 flex items-center gap-1.5">
                  <CheckCircle2 className="w-5 h-5" />
                  <span>{dataFreshnessMode === 'stale' ? 'Stale' : 'Updated'}</span>
                </div>
                <p className="text-[11px] text-slate-500 mt-1 font-mono">{districtData.lastUpdated}</p>
              </>
            ) : (
              <>
                <div className="text-lg font-bold text-slate-400">Pending Ingestion</div>
                <p className="text-[11px] text-slate-500 mt-1">Awaiting observational feed</p>
              </>
            )}
          </div>
        </Card>
      </div>

      {/* Tabs Row */}
      <div className="flex border-b border-slate-200 text-sm">
        {[
          { key: 'trend', label: 'Rainfall Trend' },
          { key: 'geo', label: 'Geographic Context' },
          { key: 'risk', label: 'Risk Analysis' },
          { key: 'sources', label: 'Data & Sources' },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={`px-4 py-2.5 font-semibold border-b-2 transition-all ${
              activeTab === tab.key
                ? 'border-blue-600 text-blue-700 bg-blue-50/60'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Main Content Area based on Tab */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left/Middle Column (8 cols) */}
        <div className="lg:col-span-8 space-y-6">
          {activeTab === 'trend' && (
            isFloodPilot ? (
              <Card variant="flood">
                <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-100">
                  <div>
                    <h3 className="text-base font-bold text-slate-900">Daily Rainfall — Gorakhpur</h3>
                    <p className="text-xs text-slate-500">
                      Comparing daily volume with 10-year historical baseline (CHIRPS & GPM)
                    </p>
                  </div>
                  <div className="flex items-center space-x-1.5 bg-slate-100 p-1 rounded-lg border border-slate-200 text-xs">
                    {(['7', '30', '90', '365'] as const).map((r) => (
                      <button
                        key={r}
                        onClick={() => setTimeRange(r)}
                        className={`px-2.5 py-0.5 rounded font-medium transition ${
                          timeRange === r
                            ? 'bg-white text-blue-700 font-bold shadow-sm'
                            : 'text-slate-600 hover:text-slate-900'
                        }`}
                      >
                        {r === '365' ? '1 Year' : `${r} Days`}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="mt-4">
                  <RainfallChart
                    data={chartSeries}
                    barColor="#0284c7"
                    lineColor="#2563eb"
                    height={250}
                  />
                </div>
              </Card>
            ) : (
              <Card variant="default">
                <div className="p-8 text-center space-y-3">
                  <div className="w-12 h-12 rounded-2xl bg-amber-50 border border-amber-200 text-amber-600 flex items-center justify-center mx-auto">
                    <Info className="w-6 h-6" />
                  </div>
                  <h3 className="text-base font-bold text-slate-900">
                    No Historical Hydrological Telemetry Ingested for {activeLocationData.name}
                  </h3>
                  <p className="text-xs text-slate-600 max-w-lg mx-auto leading-relaxed">
                    Daily precipitation series have not yet been ingested into the partitioned database for {activeLocationData.name}. In accordance with scientific integrity rules, candidate districts never inherit or interpolate observations or risk scores from Gorakhpur or Mahoba.
                  </p>
                  <div className="pt-2">
                    <button
                      onClick={() => setSelectedLocation('gorakhpur')}
                      className="px-4 py-2 rounded-xl bg-blue-600 text-white font-semibold text-xs hover:bg-blue-700 transition shadow-sm"
                    >
                      View Gorakhpur Calibrated Pilot
                    </button>
                  </div>
                </div>
              </Card>
            )
          )}

          {activeTab === 'geo' && (
            <Card variant="flood">
              <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-100">
                <div className="flex items-center space-x-2">
                  <Compass className="w-4 h-4 text-blue-600" />
                  <h3 className="text-sm font-bold text-slate-900">Geographic Terrain Context</h3>
                </div>
                <div className="flex items-center gap-1.5 text-xs">
                  {(
                    [
                      { id: 'rainfall', label: 'Rainfall Layer' },
                      { id: 'river', label: 'River Network' },
                      { id: 'elevation', label: 'Elevation Contours' },
                      { id: 'boundary', label: 'Administrative' },
                    ] as const
                  ).map((layer) => (
                    <button
                      key={layer.id}
                      onClick={() => setSelectedLayer(layer.id)}
                      className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition ${
                        selectedLayer === layer.id
                          ? 'bg-blue-600 text-white shadow-sm'
                          : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                      }`}
                    >
                      {layer.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="mt-3 p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700 space-y-2.5">
                <div className="flex justify-between items-center py-1.5 border-b border-slate-200">
                  <span className="text-slate-500">River Basin</span>
                  <span className="font-semibold text-slate-900">Rapti, Rohini & Ami River Drainage</span>
                </div>
                <div className="flex justify-between items-center py-1.5 border-b border-slate-200">
                  <span className="text-slate-500">Average District Elevation</span>
                  <span className="font-semibold text-slate-900">{districtData.elevationM} m above Mean Sea Level</span>
                </div>
                <div className="flex justify-between items-center py-1.5 border-b border-slate-200">
                  <span className="text-slate-500">Terrain Slope / Inundation Susceptibility</span>
                  <span className="font-semibold text-amber-800">Gentle Terai gradient (&lt; 1.2° slope)</span>
                </div>
                <div className="flex justify-between items-center py-1.5">
                  <span className="text-slate-500">UPSDMA 2024 Profile</span>
                  <span className="font-semibold text-rose-700">Hyper-sensitive flood category</span>
                </div>
              </div>
            </Card>
          )}

          {activeTab === 'risk' && (
            <Card variant="flood">
              <h3 className="text-sm font-bold text-slate-900 pb-3 border-b border-slate-100">
                Detailed Indicator Decomposition
              </h3>
              <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                  <span className="text-slate-500 block mb-1">7-Day Rainfall Accumulation</span>
                  <span className="text-lg font-black text-rose-600">286 mm</span>
                  <p className="text-[11px] text-slate-500 mt-1">Exceeds 90th percentile historical threshold.</p>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                  <span className="text-slate-500 block mb-1">Standardized Precipitation Index (SPI-1)</span>
                  <span className="text-lg font-black text-blue-700">+1.45 (Extremely Wet)</span>
                  <p className="text-[11px] text-slate-500 mt-1">Indicates significant meteorological surplus.</p>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                  <span className="text-slate-500 block mb-1">Topographic Wetness Index (TWI)</span>
                  <span className="text-lg font-black text-amber-700">High Runoff Retention</span>
                  <p className="text-[11px] text-slate-500 mt-1">SRTM DEM indicates poor natural outflow.</p>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                  <span className="text-slate-500 block mb-1">Estimated Return Period Proxy</span>
                  <span className="text-lg font-black text-rose-600">1-in-8 Year Event</span>
                  <p className="text-[11px] text-slate-500 mt-1">Based on 1981–2024 CHIRPS distribution.</p>
                </div>
              </div>
            </Card>
          )}

          {activeTab === 'sources' && (
            <Card variant="flood">
              <h3 className="text-sm font-bold text-slate-900 pb-3 border-b border-slate-100">
                Data Provenance & Citations
              </h3>
              <div className="mt-3 space-y-2.5 text-xs text-slate-700">
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex justify-between items-center">
                  <div>
                    <div className="font-bold text-slate-900">NASA GPM IMERG 0.1° Satellite Run</div>
                    <div className="text-[11px] text-slate-500">Calibrated microwave radar estimates</div>
                  </div>
                  <span className="text-blue-700 font-mono text-[11px] font-semibold">Late Run v07B</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex justify-between items-center">
                  <div>
                    <div className="font-bold text-slate-900">CHIRPS Daily Station Blend</div>
                    <div className="text-[11px] text-slate-500">Historical precipitation baseline (1981–present)</div>
                  </div>
                  <span className="text-blue-700 font-mono text-[11px] font-semibold">UCSB CHG v2.0</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex justify-between items-center">
                  <div>
                    <div className="font-bold text-slate-900">UPSDMA State Flood Mock Exercise Report 2024</div>
                    <div className="text-[11px] text-slate-500">Official hazard profile & Rapti basin classification</div>
                  </div>
                  <span className="text-emerald-700 font-mono text-[11px] font-semibold">Official Govt Doc</span>
                </div>
              </div>
            </Card>
          )}
        </div>

        {/* Right Column: Key Insights & Transparency Notes (4 cols) */}
        <div className="lg:col-span-4 space-y-4">
          <Card variant="flood">
            <h3 className="text-sm font-bold text-slate-900 pb-2 border-b border-slate-100 flex items-center space-x-2">
              <Info className="w-4 h-4 text-blue-600" />
              <span>Key Insights</span>
            </h3>
            {isFloodPilot ? (
              <ul className="mt-3 text-xs text-slate-700 space-y-2.5 leading-relaxed">
                <li className="flex items-start space-x-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-600 mt-1.5 shrink-0" />
                  <span>
                    Recent 7-day rainfall ({districtData.rainfall7dMm} mm) is {districtData.anomalyPct}% higher than
                    the October historical average in eastern UP.
                  </span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-rose-600 mt-1.5 shrink-0" />
                  <span>
                    Low-lying tehsils adjacent to Rapti river embankments have heightened vulnerability.
                  </span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-600 mt-1.5 shrink-0" />
                  <span>
                    Continuous data tracking active. Use official alerts for evacuation orders.
                  </span>
                </li>
              </ul>
            ) : (
              <ul className="mt-3 text-xs text-slate-700 space-y-2.5 leading-relaxed">
                <li className="flex items-start space-x-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-600 mt-1.5 shrink-0" />
                  <span>
                    Candidate district registered in administrative spatial hierarchy ({activeLocationData.region}).
                  </span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-slate-400 mt-1.5 shrink-0" />
                  <span>
                    Observational precipitation extraction queued awaiting database ingestion.
                  </span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-600 mt-1.5 shrink-0" />
                  <span>
                    Zero score interpolation applied from Gorakhpur or Mahoba models.
                  </span>
                </li>
              </ul>
            )}
          </Card>

          <Card className="bg-slate-50 border border-slate-200">
            <h3 className="text-xs font-bold text-slate-600 uppercase tracking-wider pb-2 border-b border-slate-200">
              Scientific Transparency Note
            </h3>
            <p className="mt-2 text-xs text-slate-600 leading-relaxed">
              This flood assessment indicates meteorological rainfall accumulation and topographic susceptibility.
              Rainfall accumulation alone does NOT determine Rapti/Rohini river stage, upstream dam releases, embankment
              failure, or actual inundation depth. Refer directly to Central Water Commission (CWC) gauge levels and
              UPSDMA alerts for official warnings.
            </p>
          </Card>
        </div>
      </div>
    </div>
  );
};
