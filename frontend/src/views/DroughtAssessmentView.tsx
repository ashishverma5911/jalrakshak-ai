import React, { useState, useEffect } from 'react';
import {
  Sun,
  Flame,
  AlertCircle,
  Clock,
  Compass,
  Layers,
  ChevronDown,
  Info,
  CheckCircle2,
  TrendingDown,
  Sprout,
  Activity,
  Calendar,
  RefreshCw,
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
    isConfiguredPilot,
  } = useApp();
  const [activeTab, setActiveTab] = useState<'rainfall' | 'comparison' | 'indicators' | 'sources'>('rainfall');
  const [viewMode, setViewMode] = useState<'monthly' | 'weekly'>('monthly');
  const [backendData, setBackendData] = useState<HazardAssessmentResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const districtData = UP_DISTRICTS_DATA.find((d) => d.id === 'mahoba')!;
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
    loadBackendDrought();
  }, []);

  const r90d = backendData?.indicators.find((i) => i.indicator_id === 'mahoba_rain_90d')?.value ?? districtData.rainfall90dMm;
  const anom90d = backendData?.indicators.find((i) => i.indicator_id === 'mahoba_anomaly_90d')?.value ?? districtData.anomalyPct;
  const kharifDef = backendData?.indicators.find((i) => i.indicator_id === 'mahoba_kharif_deficit')?.value ?? districtData.seasonalDeficitPct;
  const spi3 = backendData?.indicators.find((i) => i.indicator_id === 'mahoba_spi_3')?.value ?? districtData.spi3;
  const dryDays = backendData?.indicators.find((i) => i.indicator_id === 'mahoba_consecutive_dry_days')?.value ?? 22;

  return (
    <div className="space-y-6">
      {/* Demo Data Disclaimer */}
      <div className="px-3.5 py-1.5 rounded-xl bg-amber-950/40 border border-amber-800/40 text-[11px] text-amber-300 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
          <span>{DEMO_DATA_DISCLAIMER}</span>
        </div>
        <span className="font-mono text-amber-400">PILOT: MAHOBA</span>
      </div>

      {/* Scope Alert when a candidate district or non-drought district is active */}
      {selectedLocation !== 'mahoba' && (
        <div className="p-3.5 rounded-2xl bg-amber-950/60 border border-amber-500/40 text-xs text-amber-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-md">
          <div className="flex items-center space-x-2.5">
            <Info className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              <strong>Hazard Pilot Scope:</strong> Mahoba is currently the active drought pilot. {activeLocationData.name} ({activeLocationData.region}) is not configured for meteorological drought indicators. Displaying Mahoba pilot benchmark data below.
            </span>
          </div>
          <button
            onClick={() => setSelectedLocation('mahoba')}
            className="px-3 py-1 rounded-xl bg-amber-500 text-navy-950 font-semibold hover:bg-amber-400 transition shrink-0"
          >
            Focus Mahoba
          </button>
        </div>
      )}

      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-navy-800">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-bold uppercase tracking-wider text-amber-400 bg-amber-950/70 px-2 py-0.5 rounded border border-amber-800/80">
              Hazard Pilot 2
            </span>
            <span className="text-xs text-amber-200/70 font-mono">Bundelkhand Plateau Context</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-extrabold text-white mt-1">
            Mahoba — Drought Assessment
          </h1>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <DataProvenanceBadge
              mode={backendData?.data_mode || 'CACHED_VERIFIED'}
              source="CHIRPS v2.0 / 30-Year Climatology (1991–2020)"
              datasetVersion="v2.0"
              spatialResolution="0.05° (~5.3 km)"
              limitations="Spatial area-weighted aggregation over Mahoba boundary polygon. SPI-3 calculated via WMO 2-parameter Gamma MLE."
            />
            <p className="text-xs text-slate-300">
              Analyse seasonal rainfall deficits, SPI indicators and agricultural drought stress signals.
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
            className="bg-navy-850 border border-amber-500/40 text-xs font-semibold text-amber-200 rounded-xl px-3 py-2 focus:outline-none focus:border-amber-400"
          >
            <option value="mahoba">Mahoba (Drought Pilot)</option>
            <option value="gorakhpur">Switch to Gorakhpur (Flood)</option>
            {selectedLocation !== 'mahoba' && selectedLocation !== 'gorakhpur' && (
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
            <span className="text-xs text-amber-200/80 font-medium">Current Risk Level</span>
            <Badge label="MODERATE" riskLevel="moderate" dot />
          </div>
          <div className="mt-3">
            <div className="text-2xl font-black text-amber-400 flex items-center gap-1.5">
              <Flame className="w-6 h-6 text-amber-400" />
              <span>Moderate Risk</span>
            </div>
            <p className="text-[11px] text-amber-100/70 mt-1">
              Rainfall is below historical average for this period.
            </p>
          </div>
        </Card>

        {/* Metric 2: 90-Day Cumulative Rainfall */}
        <Card variant="drought">
          <div className="flex items-center justify-between">
            <span className="text-xs text-amber-200/80 font-medium">90-Day Rainfall</span>
            <span className="text-xs text-rose-400 font-bold">{typeof anom90d === 'number' ? anom90d.toFixed(1) : anom90d}% vs normal</span>
          </div>
          <div className="mt-3">
            <div className="text-3xl font-black text-white">
              {typeof r90d === 'number' ? r90d.toFixed(1) : r90d} <span className="text-sm font-semibold text-slate-400">mm</span>
            </div>
            <p className="text-[11px] text-amber-300 mt-1">Accumulated CHIRPS precipitation</p>
          </div>
        </Card>

        {/* Metric 3: Seasonal Deficit */}
        <Card variant="drought">
          <div className="flex items-center justify-between">
            <span className="text-xs text-amber-200/80 font-medium">Seasonal Deficit</span>
            <span className="text-xs text-rose-400 font-bold">Severe</span>
          </div>
          <div className="mt-3">
            <div className="text-3xl font-black text-rose-400">{typeof kharifDef === 'number' ? kharifDef.toFixed(1) : kharifDef}%</div>
            <p className="text-[11px] text-amber-200/70 mt-1">Kharif / Monsoon departure</p>
          </div>
        </Card>

        {/* Metric 4: Data Freshness */}
        <Card variant="drought">
          <div className="flex items-center justify-between">
            <span className="text-xs text-amber-200/80 font-medium">Data Freshness</span>
            <span
              className={`w-2 h-2 rounded-full ${
                dataFreshnessMode === 'stale' ? 'bg-amber-400' : 'bg-emerald-400 animate-pulse'
              }`}
            />
          </div>
          <div className="mt-3">
            <div className="text-xl font-bold text-emerald-400 flex items-center gap-1.5">
              <CheckCircle2 className="w-5 h-5" />
              <span>{dataFreshnessMode === 'stale' ? 'Stale' : 'Updated'}</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1 font-mono">{districtData.lastUpdated}</p>
          </div>
        </Card>
      </div>

      {/* Tabs Row */}
      <div className="flex border-b border-navy-800 text-sm">
        {[
          { key: 'rainfall', label: 'Rainfall Analysis' },
          { key: 'comparison', label: 'Historical Comparison' },
          { key: 'indicators', label: 'Risk Indicators' },
          { key: 'sources', label: 'Data & Sources' },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={`px-4 py-2.5 font-medium border-b-2 transition-all ${
              activeTab === tab.key
                ? 'border-amber-400 text-amber-300 bg-amber-950/30'
                : 'border-transparent text-slate-400 hover:text-slate-200'
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
            <Card variant="drought">
              <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-navy-800">
                <div>
                  <h3 className="text-base font-bold text-white">Precipitation Series — Mahoba</h3>
                  <p className="text-xs text-slate-400">Current Year vs Historical 10-Year Average</p>
                </div>
                <div className="flex items-center space-x-1.5 bg-navy-900 p-1 rounded-lg border border-navy-800 text-xs">
                  <button
                    onClick={() => setViewMode('monthly')}
                    className={`px-2.5 py-1 rounded font-semibold transition ${
                      viewMode === 'monthly' ? 'bg-amber-500 text-navy-950 font-bold' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Monthly
                  </button>
                  <button
                    onClick={() => setViewMode('weekly')}
                    className={`px-2.5 py-1 rounded font-semibold transition ${
                      viewMode === 'weekly' ? 'bg-amber-500 text-navy-950 font-bold' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Weekly
                  </button>
                </div>
              </div>
              <div className="mt-4">
                <RainfallChart
                  data={chartSeries}
                  barColor="#f59e0b"
                  lineColor="#ea580c"
                  height={250}
                />
              </div>
            </Card>
          )}

          {activeTab === 'comparison' && (
            <Card variant="drought">
              <h3 className="text-sm font-bold text-white pb-3 border-b border-navy-800">
                Monsoon Seasonal Deficit vs Normal (Bundelkhand)
              </h3>
              <div className="mt-3 p-4 rounded-xl bg-navy-900 border border-navy-800 space-y-3 text-xs">
                <div className="flex justify-between items-center py-1 border-b border-navy-850">
                  <span className="text-slate-400">Kharif Normal Rainfall (10-Yr Baseline)</span>
                  <span className="font-semibold text-white">820 mm</span>
                </div>
                <div className="flex justify-between items-center py-1 border-b border-navy-850">
                  <span className="text-slate-400">2026 Observed Monsoon Inflow</span>
                  <span className="font-semibold text-rose-400">230 mm (-72% Departure)</span>
                </div>
                <div className="flex justify-between items-center py-1 border-b border-navy-850">
                  <span className="text-slate-400">Rainfall Category (IMD Standard)</span>
                  <span className="font-semibold text-rose-400">Scanty / Large Deficient</span>
                </div>
                <div className="flex justify-between items-center py-1">
                  <span className="text-slate-400">Aquifer Type</span>
                  <span className="font-semibold text-amber-300">Crystalline Granite Fractures (Poor storage)</span>
                </div>
              </div>
            </Card>
          )}

          {activeTab === 'indicators' && (
            <Card variant="drought">
              <h3 className="text-sm font-bold text-white pb-3 border-b border-navy-800">
                Drought Indices Breakdown
              </h3>
              <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-xl bg-navy-900 border border-navy-800">
                  <span className="text-slate-400 block mb-1">Standardized Precipitation Index (SPI-3)</span>
                  <span className="text-lg font-black text-rose-400">{districtData.spi3} (Severely Dry)</span>
                  <p className="text-[11px] text-slate-400 mt-1">Calculated over 90-day monsoon window.</p>
                </div>
                <div className="p-3 rounded-xl bg-navy-900 border border-navy-800">
                  <span className="text-slate-400 block mb-1">Consecutive Dry Spell Days</span>
                  <span className="text-lg font-black text-amber-300">22 Days (&lt; 1 mm)</span>
                  <p className="text-[11px] text-slate-400 mt-1">High evaporative demand in October.</p>
                </div>
                <div className="p-3 rounded-xl bg-navy-900 border border-navy-800">
                  <span className="text-slate-400 block mb-1">Soil Moisture Stress Proxy</span>
                  <span className="text-lg font-black text-rose-400">High Agricultural Stress</span>
                  <p className="text-[11px] text-slate-400 mt-1">Critical stage for rabi sowing preparation.</p>
                </div>
                <div className="p-3 rounded-xl bg-navy-900 border border-navy-800">
                  <span className="text-slate-400 block mb-1">Groundwater Dependency</span>
                  <span className="text-lg font-black text-amber-300">High / Vulnerable</span>
                  <p className="text-[11px] text-slate-400 mt-1">Low open-well recharge recorded in Bundelkhand.</p>
                </div>
              </div>
            </Card>
          )}

          {activeTab === 'sources' && (
            <Card variant="drought">
              <h3 className="text-sm font-bold text-white pb-3 border-b border-navy-800">
                Data Provenance & Citations
              </h3>
              <div className="mt-3 space-y-2.5 text-xs text-slate-300">
                <div className="p-3 rounded-xl bg-navy-900 border border-navy-800 flex justify-between items-center">
                  <div>
                    <div className="font-bold text-white">CHIRPS Daily Station Blended Precipitation</div>
                    <div className="text-[11px] text-slate-400">1981–present 40-year climatological baseline</div>
                  </div>
                  <span className="text-amber-400 font-mono text-[11px]">UCSB CHG</span>
                </div>
                <div className="p-3 rounded-xl bg-navy-900 border border-navy-800 flex justify-between items-center">
                  <div>
                    <div className="font-bold text-white">Manual for Drought Management 2020</div>
                    <div className="text-[11px] text-slate-400">Ministry of Agriculture & Farmers Welfare, India</div>
                  </div>
                  <span className="text-emerald-400 font-mono text-[11px]">Govt Guidelines</span>
                </div>
              </div>
            </Card>
          )}
        </div>

        {/* Right Column: Key Insights */}
        <div className="lg:col-span-4 space-y-4">
          <Card variant="drought">
            <h3 className="text-sm font-bold text-white pb-2 border-b border-navy-800 flex items-center space-x-2">
              <Info className="w-4 h-4 text-amber-400" />
              <span>Key Insights</span>
            </h3>
            <ul className="mt-3 text-xs text-slate-300 space-y-2.5 leading-relaxed">
              <li className="flex items-start space-x-2">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-400 mt-1.5 shrink-0" />
                <span>
                  Rainfall is significantly below the historical average for this period ({districtData.anomalyPct}% anomaly).
                </span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-1.5 shrink-0" />
                <span>Prolonged dry conditions observed across the southern Bundelkhand belt.</span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="w-1.5 h-1.5 rounded-full bg-orange-400 mt-1.5 shrink-0" />
                <span>Agricultural and water resources may experience stress during Rabi sowing.</span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 mt-1.5 shrink-0" />
                <span>Water conservation and efficient irrigation usage is strongly recommended.</span>
              </li>
            </ul>
          </Card>

          <Card className="bg-navy-900/60 border border-navy-800">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider pb-2 border-b border-navy-800">
              Scientific Transparency Note
            </h3>
            <p className="mt-2 text-xs text-slate-400 leading-relaxed">
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
