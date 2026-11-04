import React, { useState, useEffect } from 'react';
import {
  Flame,
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

export const DroughtAssessmentView: React.FC = () => {
  const {
    selectedLocation,
    setSelectedLocation,
    setCurrentRoute,
    dataFreshnessMode,
    activeLocationData,
  } = useApp();
  const [activeTab, setActiveTab] = useState<'rainfall' | 'comparison' | 'indicators' | 'sources'>('rainfall');
  const [viewMode, setViewMode] = useState<'monthly' | 'weekly'>('monthly');
  const [backendData, setBackendData] = useState<HazardAssessmentResponse | null>(null);
  const [, setIsLoading] = useState<boolean>(false);
  const [, setFetchError] = useState<string | null>(null);

  const districtData = UP_DISTRICTS_DATA.find((d) => d.id === 'mahoba')!;
  const isDroughtPilot = selectedLocation === 'mahoba';
  const chartSeries = getFilteredRainfallData('mahoba', '365', viewMode === 'monthly' ? 'monthly' : 'weekly');

  const loadBackendDrought = () => {
    setIsLoading(true);
    setFetchError(null);
    apiService
      .fetchDroughtRisk('mahoba')
      .then((data) => {
        setBackendData(data);
      })
      .catch((err) => {
        setFetchError(err.message || 'Failed to fetch backend drought assessment');
      })
      .finally(() => {
        setIsLoading(false);
      });
  };

  useEffect(() => {
    if (isDroughtPilot) {
      loadBackendDrought();
    }
  }, [selectedLocation, isDroughtPilot]);

  const ind90d = backendData?.indicators.find((i) => i.indicator_id === 'drought_precip_90d_accum' || i.indicator_id === 'mahoba_rain_90d');
  const r90d = ind90d !== undefined ? ind90d.value : districtData.rainfall90dMm;
  const indAnom90d = backendData?.indicators.find((i) => i.indicator_id === 'drought_precip_90d_anomaly' || i.indicator_id === 'mahoba_anomaly_90d');
  const anom90d = indAnom90d !== undefined ? indAnom90d.value : districtData.anomalyPct;
  const indKharif = backendData?.indicators.find((i) => i.indicator_id === 'drought_seasonal_deficit' || i.indicator_id === 'mahoba_kharif_deficit');
  const kharifDef = indKharif !== undefined ? indKharif.value : districtData.seasonalDeficitPct;

  return (
    <div className="space-y-6">
      {/* Demo Data Disclaimer */}
      <div className="px-3.5 py-1.5 rounded-xl bg-amber-50 border border-amber-200 text-[11px] text-amber-800 flex items-center justify-between shadow-sm">
        <div className="flex items-center space-x-2">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-600" />
          <span>{DEMO_DATA_DISCLAIMER}</span>
        </div>
        <span className="font-mono text-amber-800 font-semibold">
          {isDroughtPilot ? 'PILOT: MAHOBA' : `CANDIDATE: ${activeLocationData.name.toUpperCase()}`}
        </span>
      </div>

      {/* Scope Alert when a candidate district or non-drought district is active */}
      {!isDroughtPilot && (
        <div className="p-3.5 rounded-2xl bg-amber-50 border border-amber-200 text-xs text-amber-900 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm">
          <div className="flex items-center space-x-2.5">
            <Info className="w-4 h-4 text-amber-600 shrink-0" />
            <span>
              <strong>Hazard Pilot Scope:</strong> Mahoba is currently the active drought pilot. {activeLocationData.name} ({activeLocationData.region}) is not configured for meteorological drought indicators.
            </span>
          </div>
          <button
            onClick={() => setSelectedLocation('mahoba')}
            className="px-3 py-1 rounded-xl bg-amber-600 text-white font-semibold hover:bg-amber-700 transition shrink-0"
          >
            Focus Mahoba
          </button>
        </div>
      )}

      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            {isDroughtPilot ? (
              <>
                <span className="text-xs font-bold uppercase tracking-wider text-amber-800 bg-amber-100 px-2 py-0.5 rounded border border-amber-200">
                  Hazard Pilot 2
                </span>
                <span className="text-xs text-slate-500 font-mono">Bundelkhand Plateau Context</span>
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
            {isDroughtPilot ? 'Mahoba — Drought Assessment' : `${activeLocationData.name} — Drought Assessment`}
          </h1>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <DataProvenanceBadge
              mode={isDroughtPilot ? (backendData?.data_mode || 'CACHED_VERIFIED') : 'DATA_PENDING'}
              source={isDroughtPilot ? "CHIRPS v2.0 / 30-Year Climatology (1991–2020)" : "Observational Ingestion Stream Unlinked"}
              datasetVersion={isDroughtPilot ? "v2.0" : "Pending Ingestion"}
              spatialResolution={isDroughtPilot ? "0.05° (~5.3 km)" : "WGS84 Centroid Point"}
              limitations={isDroughtPilot ? "Spatial area-weighted aggregation over Mahoba boundary polygon. SPI-3 calculated via WMO 2-parameter Gamma MLE." : "Scientific Boundary: Candidate districts never inherit or interpolate observational telemetry or risk scores from Gorakhpur or Mahoba."}
            />
            <p className="text-xs text-slate-600">
              {isDroughtPilot
                ? "Analyse seasonal rainfall deficits, SPI indicators and agricultural drought stress signals."
                : `Meteorological drought indicators are unconfigured for ${activeLocationData.name}. Zero score interpolation applied.`}
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <select
            value={selectedLocation}
            onChange={(e) => {
              if (e.target.value === 'gorakhpur') {
                setSelectedLocation('gorakhpur');
                setCurrentRoute('flood');
              } else {
                setSelectedLocation(e.target.value as any);
              }
            }}
            className="bg-white border border-slate-200 text-xs font-semibold text-slate-800 rounded-xl px-3 py-2 shadow-sm focus:outline-none focus:border-blue-500"
          >
            <option value="mahoba">Mahoba (Drought Pilot)</option>
            <option value="gorakhpur">Switch to Gorakhpur (Flood)</option>
            {!isDroughtPilot && selectedLocation !== 'gorakhpur' && (
              <option value={selectedLocation}>{activeLocationData.name} (Candidate District)</option>
            )}
          </select>
        </div>
      </div>

      {/* Top 4 Indicator Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Current Risk Level */}
        <Card variant="drought" className="relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500 font-medium">Current Risk Level</span>
            {isDroughtPilot ? (
              <Badge label="MODERATE" riskLevel="moderate" dot />
            ) : (
              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                Pending
              </span>
            )}
          </div>
          <div className="mt-3">
            {isDroughtPilot ? (
              <>
                <div className="text-2xl font-black text-amber-700 flex items-center gap-1.5">
                  <Flame className="w-6 h-6 text-amber-600" />
                  <span>Moderate Risk</span>
                </div>
                <p className="text-[11px] text-slate-600 mt-1">
                  Rainfall is below historical average for this period.
                </p>
              </>
            ) : (
              <>
                <div className="text-xl font-bold text-slate-400">Model Offline</div>
                <p className="text-[11px] text-slate-500 mt-1">
                  Drought modeling unconfigured for {activeLocationData.name}.
                </p>
              </>
            )}
          </div>
        </Card>

        {/* Metric 2: 90-Day Cumulative Rainfall */}
        <Card variant="drought">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500 font-medium">90-Day Rainfall</span>
            {isDroughtPilot ? (
              r90d === null || anom90d === null ? (
                <span className="text-[10px] font-mono text-amber-800 bg-amber-100 px-2 py-0.5 rounded border border-amber-200">
                  DATA UNAVAILABLE
                </span>
              ) : (
                <span className="text-xs text-rose-600 font-bold">{typeof anom90d === 'number' ? anom90d.toFixed(1) : anom90d}% vs normal</span>
              )
            ) : (
              <span className="text-[10px] font-mono text-slate-400">DATA PENDING</span>
            )}
          </div>
          <div className="mt-3">
            {isDroughtPilot ? (
              r90d === null ? (
                <>
                  <div className="text-3xl font-black text-slate-400">
                    -- <span className="text-sm font-semibold text-slate-400">mm</span>
                  </div>
                  <p className="text-[11px] text-amber-800 mt-1 font-medium">
                    90-day rainfall data unavailable — insufficient historical coverage
                  </p>
                </>
              ) : (
                <>
                  <div className="text-3xl font-black text-slate-900">
                    {typeof r90d === 'number' ? r90d.toFixed(1) : r90d} <span className="text-sm font-semibold text-slate-500">mm</span>
                  </div>
                  <p className="text-[11px] text-amber-800 mt-1 font-medium">Accumulated precipitation</p>
                </>
              )
            ) : (
              <>
                <div className="text-3xl font-black text-slate-400">-- <span className="text-sm font-semibold text-slate-400">mm</span></div>
                <p className="text-[11px] text-slate-500 mt-1">Station telemetry stream unlinked</p>
              </>
            )}
          </div>
        </Card>

        {/* Metric 3: Seasonal Deficit */}
        <Card variant="drought">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500 font-medium">Seasonal Deficit</span>
            {isDroughtPilot ? (
              kharifDef === null ? (
                <span className="text-[10px] font-mono text-amber-800 bg-amber-100 px-2 py-0.5 rounded border border-amber-200">
                  DATA UNAVAILABLE
                </span>
              ) : (
                <span className="text-xs text-rose-600 font-bold">Severe</span>
              )
            ) : (
              <span className="text-[10px] font-mono text-slate-400">DATA PENDING</span>
            )}
          </div>
          <div className="mt-3">
            {isDroughtPilot ? (
              kharifDef === null ? (
                <>
                  <div className="text-3xl font-black text-slate-400">--%</div>
                  <p className="text-[11px] text-amber-800 mt-1 font-medium">Monsoon departure data unavailable</p>
                </>
              ) : (
                <>
                  <div className="text-3xl font-black text-rose-600">{typeof kharifDef === 'number' ? kharifDef.toFixed(1) : kharifDef}%</div>
                  <p className="text-[11px] text-amber-800 mt-1 font-medium">Kharif / Monsoon departure</p>
                </>
              )
            ) : (
              <>
                <div className="text-3xl font-black text-slate-400">--%</div>
                <p className="text-[11px] text-slate-500 mt-1">30-year climatology uncalibrated</p>
              </>
            )}
          </div>
        </Card>

        {/* Metric 4: Data Freshness */}
        <Card variant="drought">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500 font-medium">Data Freshness</span>
            <span
              className={`w-2 h-2 rounded-full ${
                !isDroughtPilot ? 'bg-slate-300' : dataFreshnessMode === 'stale' ? 'bg-amber-500' : 'bg-emerald-500 animate-pulse'
              }`}
            />
          </div>
          <div className="mt-3">
            {isDroughtPilot ? (
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
          { key: 'rainfall', label: 'Rainfall Analysis' },
          { key: 'comparison', label: 'Historical Comparison' },
          { key: 'indicators', label: 'Risk Indicators' },
          { key: 'sources', label: 'Data & Sources' },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={`px-4 py-2.5 font-semibold border-b-2 transition-all ${
              activeTab === tab.key
                ? 'border-amber-600 text-amber-800 bg-amber-50/60'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-8 space-y-6">
          {activeTab === 'rainfall' && (
            isDroughtPilot ? (
              <Card variant="drought">
                <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-100">
                  <div>
                    <h3 className="text-base font-bold text-slate-900">Precipitation Series — Mahoba</h3>
                    <p className="text-xs text-slate-500">Current Year vs Historical 10-Year Average</p>
                  </div>
                  <div className="flex items-center space-x-1.5 bg-slate-100 p-1 rounded-lg border border-slate-200 text-xs">
                    <button
                      onClick={() => setViewMode('monthly')}
                      className={`px-2.5 py-1 rounded font-semibold transition ${
                        viewMode === 'monthly' ? 'bg-white text-amber-800 font-bold shadow-sm' : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      Monthly
                    </button>
                    <button
                      onClick={() => setViewMode('weekly')}
                      className={`px-2.5 py-1 rounded font-semibold transition ${
                        viewMode === 'weekly' ? 'bg-white text-amber-800 font-bold shadow-sm' : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      Weekly
                    </button>
                  </div>
                </div>
                <div className="mt-4">
                  <RainfallChart
                    data={chartSeries}
                    barColor="#d97706"
                    lineColor="#ea580c"
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
                    No Meteorological Drought Telemetry Ingested for {activeLocationData.name}
                  </h3>
                  <p className="text-xs text-slate-600 max-w-lg mx-auto leading-relaxed">
                    Long-term 90-day seasonal rainfall series and climatological departures have not yet been ingested into the partitioned database for {activeLocationData.name}. In accordance with scientific integrity rules, candidate districts never inherit or interpolate observations or drought indices from Mahoba or Gorakhpur.
                  </p>
                  <div className="pt-2">
                    <button
                      onClick={() => setSelectedLocation('mahoba')}
                      className="px-4 py-2 rounded-xl bg-amber-600 text-white font-semibold text-xs hover:bg-amber-700 transition shadow-sm"
                    >
                      View Mahoba Calibrated Pilot
                    </button>
                  </div>
                </div>
              </Card>
            )
          )}

          {activeTab === 'comparison' && (
            isDroughtPilot ? (
              <Card variant="drought">
                <h3 className="text-sm font-bold text-slate-900 pb-3 border-b border-slate-100">
                  Monsoon Seasonal Deficit vs Normal (Bundelkhand)
                </h3>
                <div className="mt-3 p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3 text-xs text-slate-700">
                  <div className="flex justify-between items-center py-1 border-b border-slate-200">
                    <span className="text-slate-500">Kharif Normal Rainfall (10-Yr Baseline)</span>
                    <span className="font-semibold text-slate-900">820 mm</span>
                  </div>
                  <div className="flex justify-between items-center py-1 border-b border-slate-200">
                    <span className="text-slate-500">2026 Observed Monsoon Inflow</span>
                    <span className="font-semibold text-rose-600">230 mm (-72% Departure)</span>
                  </div>
                  <div className="flex justify-between items-center py-1 border-b border-slate-200">
                    <span className="text-slate-500">Rainfall Category (IMD Standard)</span>
                    <span className="font-semibold text-rose-600">Scanty / Large Deficient</span>
                  </div>
                  <div className="flex justify-between items-center py-1">
                    <span className="text-slate-500">Aquifer Type</span>
                    <span className="font-semibold text-amber-800">Crystalline Granite Fractures (Poor storage)</span>
                  </div>
                </div>
              </Card>
            ) : (
              <Card variant="default">
                <div className="p-6 text-center space-y-2">
                  <h4 className="text-sm font-bold text-slate-800">Historical Monsoon Baseline Uncalibrated</h4>
                  <p className="text-xs text-slate-500 max-w-md mx-auto">
                    30-year IMD monsoon climatological normals for {activeLocationData.name} ({activeLocationData.region}) will be computed upon station record ingestion.
                  </p>
                </div>
              </Card>
            )
          )}

          {activeTab === 'indicators' && (
            isDroughtPilot ? (
              <Card variant="drought">
                <h3 className="text-sm font-bold text-slate-900 pb-3 border-b border-slate-100">
                  Drought Indices Breakdown
                </h3>
                <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="text-slate-500 block mb-1">Standardized Precipitation Index (SPI-3)</span>
                    <span className="text-lg font-black text-rose-600">{districtData.spi3} (Severely Dry)</span>
                    <p className="text-[11px] text-slate-500 mt-1">Calculated over 90-day monsoon window.</p>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="text-slate-500 block mb-1">Consecutive Dry Spell Days</span>
                    <span className="text-lg font-black text-amber-700">22 Days (&lt; 1 mm)</span>
                    <p className="text-[11px] text-slate-500 mt-1">High evaporative demand in October.</p>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="text-slate-500 block mb-1">Soil Moisture Stress Proxy</span>
                    <span className="text-lg font-black text-rose-600">High Agricultural Stress</span>
                    <p className="text-[11px] text-slate-500 mt-1">Critical stage for rabi sowing preparation.</p>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="text-slate-500 block mb-1">Groundwater Dependency</span>
                    <span className="text-lg font-black text-amber-700">High / Vulnerable</span>
                    <p className="text-[11px] text-slate-500 mt-1">Low open-well recharge recorded in Bundelkhand.</p>
                  </div>
                </div>
              </Card>
            ) : (
              <Card variant="default">
                <div className="p-6 text-center space-y-2">
                  <h4 className="text-sm font-bold text-slate-800">Drought Indices Offline</h4>
                  <p className="text-xs text-slate-500 max-w-md mx-auto">
                    SPI-3, dry spell tracking, and agro-climatic stress models are awaiting primary observational data for {activeLocationData.name}.
                  </p>
                </div>
              </Card>
            )
          )}

          {activeTab === 'sources' && (
            <Card variant="drought">
              <h3 className="text-sm font-bold text-slate-900 pb-3 border-b border-slate-100">
                Data Provenance & Citations
              </h3>
              <div className="mt-3 space-y-2.5 text-xs text-slate-700">
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex justify-between items-center">
                  <div>
                    <div className="font-bold text-slate-900">CHIRPS Daily Station Blended Precipitation</div>
                    <div className="text-[11px] text-slate-500">1981–present 40-year climatological baseline</div>
                  </div>
                  <span className="text-amber-800 font-mono text-[11px] font-semibold">UCSB CHG</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex justify-between items-center">
                  <div>
                    <div className="font-bold text-slate-900">Manual for Drought Management 2020</div>
                    <div className="text-[11px] text-slate-500">Ministry of Agriculture & Farmers Welfare, India</div>
                  </div>
                  <span className="text-emerald-700 font-mono text-[11px] font-semibold">Govt Guidelines</span>
                </div>
              </div>
            </Card>
          )}
        </div>

        {/* Right Column: Key Insights */}
        <div className="lg:col-span-4 space-y-4">
          <Card variant="drought">
            <h3 className="text-sm font-bold text-slate-900 pb-2 border-b border-slate-100 flex items-center space-x-2">
              <Info className="w-4 h-4 text-amber-600" />
              <span>Key Insights</span>
            </h3>
            {isDroughtPilot ? (
              <ul className="mt-3 text-xs text-slate-700 space-y-2.5 leading-relaxed">
                <li className="flex items-start space-x-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-rose-600 mt-1.5 shrink-0" />
                  <span>
                    Rainfall is significantly below the historical average for this period ({districtData.anomalyPct}% anomaly).
                  </span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-600 mt-1.5 shrink-0" />
                  <span>Prolonged dry conditions observed across the southern Bundelkhand belt.</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-orange-600 mt-1.5 shrink-0" />
                  <span>Agricultural and water resources may experience stress during Rabi sowing.</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-600 mt-1.5 shrink-0" />
                  <span>Water conservation and efficient irrigation usage is strongly recommended.</span>
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
                    Observational precipitation and SPI baseline queued awaiting database ingestion.
                  </span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-600 mt-1.5 shrink-0" />
                  <span>
                    Zero score interpolation applied from Mahoba or Gorakhpur models.
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
              Drought assessment tracks meteorological rainfall anomalies, seasonal deficits, and SPI-3 indicators.
              Meteorological indicators do NOT directly measure root-zone soil moisture, crystalline hard-rock aquifer
              groundwater depletion, or actual agricultural crop loss without ground sensor telemetry.
            </p>
          </Card>
        </div>
      </div>
    </div>
  );
};
