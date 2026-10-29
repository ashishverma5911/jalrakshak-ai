import React, { useState, useEffect } from 'react';
import {
  Waves,
  CloudRain,
  AlertTriangle,
  Clock,
  Compass,
  Layers,
  ChevronDown,
  Info,
  CheckCircle2,
  ExternalLink,
  Activity,
  Calendar,
  RefreshCw,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { RainfallChart } from '../components/charts/RainfallChart';
import { apiService, HazardAssessmentResponse } from '../services/api';
import {
  UP_DISTRICTS_DATA,
  getFilteredRainfallData,
  DEMO_DATA_DISCLAIMER,
} from '../data/mockData';

export const FloodAssessmentView: React.FC = () => {
  const { selectedLocation, setSelectedLocation, setCurrentRoute, dataFreshnessMode } = useApp();
  const [activeTab, setActiveTab] = useState<'trend' | 'geo' | 'risk' | 'sources'>('trend');
  const [selectedLayer, setSelectedLayer] = useState<'rainfall' | 'river' | 'elevation' | 'boundary'>('rainfall');
  const [timeRange, setTimeRange] = useState<'7' | '30' | '90' | '365'>('30');
  const [backendData, setBackendData] = useState<HazardAssessmentResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const districtData = UP_DISTRICTS_DATA.find((d) => d.id === 'gorakhpur')!;
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
    loadBackendRisk();
  }, []);

  // Compute display values from live backend if available, else fallback fixture
  const r7d = backendData?.indicators.find((i) => i.indicator_id === 'gorakhpur_rain_7d')?.value ?? districtData.rainfall7dMm;
  const anom7d = backendData?.indicators.find((i) => i.indicator_id === 'gorakhpur_anomaly_7d')?.value ?? districtData.anomalyPct;
  const r30d = backendData?.indicators.find((i) => i.indicator_id === 'gorakhpur_rain_30d')?.value ?? districtData.rainfall30dMm;
  const anom30d = backendData?.indicators.find((i) => i.indicator_id === 'gorakhpur_anomaly_30d')?.value ?? 48;
  const isDemo = backendData?.is_demo_data ?? true;

  const handleLocationChange = (val: string) => {
    if (val === 'mahoba') {
      setSelectedLocation('mahoba');
      setCurrentRoute('drought');
    } else {
      setSelectedLocation('gorakhpur');
    }
  };

  return (
    <div className="space-y-6">
      {/* Demo Data Disclaimer */}
      <div className="px-3.5 py-1.5 rounded-xl bg-cyan-950/40 border border-cyan-800/40 text-[11px] text-cyan-300 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
          <span>{DEMO_DATA_DISCLAIMER}</span>
        </div>
        <span className="font-mono text-cyan-400">PILOT: GORAKHPUR</span>
      </div>

      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-navy-800">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-bold uppercase tracking-wider text-cyan-400 bg-cyan-950/70 px-2 py-0.5 rounded border border-cyan-800/80">
              Hazard Pilot 1
            </span>
            <span className="text-xs text-slate-400 font-mono">Rapti Basin Context</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-extrabold text-white mt-1">
            Gorakhpur — Flood Assessment
          </h1>
          <p className="text-xs lg:text-sm text-slate-300">
            Analyse rainfall, geographical terrain factors and heavy precipitation risk indicators.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <select
            value={selectedLocation}
            onChange={(e) => handleLocationChange(e.target.value)}
            className="bg-navy-850 border border-cyan-500/40 text-xs font-semibold text-cyan-200 rounded-xl px-3 py-2 focus:outline-none focus:border-cyan-400"
          >
            <option value="gorakhpur">Gorakhpur (Flood Pilot)</option>
            <option value="mahoba">Switch to Mahoba (Drought)</option>
          </select>
        </div>
      </div>

      {/* Top 4 Indicator Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Current Risk Level */}
        <Card variant="flood" className="relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-300 font-medium">Current Risk Level</span>
            <Badge label="HIGH" riskLevel="high" dot />
          </div>
          <div className="mt-3">
            <div className="text-2xl font-black text-rose-400 flex items-center gap-1.5">
              <AlertTriangle className="w-6 h-6 text-rose-400" />
              <span>High Risk</span>
            </div>
            <p className="text-[11px] text-slate-300 mt-1">
              Recent heavy rainfall significantly above historical average.
            </p>
          </div>
        </Card>

        {/* Metric 2: 7-Day Cumulative Rainfall */}
        <Card variant="flood">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-300 font-medium">7-Day Rainfall</span>
            <span className="text-xs text-emerald-400 font-bold">+{typeof anom7d === 'number' ? anom7d.toFixed(1) : anom7d}% vs normal</span>
          </div>
          <div className="mt-3">
            <div className="text-3xl font-black text-white">
              {typeof r7d === 'number' ? r7d.toFixed(1) : r7d} <span className="text-sm font-semibold text-slate-400">mm</span>
            </div>
            <p className="text-[11px] text-cyan-300 mt-1">NASA GPM IMERG 0.1° gridded run</p>
          </div>
        </Card>

        {/* Metric 3: 30-Day Rainfall */}
        <Card variant="flood">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-300 font-medium">30-Day Rainfall</span>
            <span className="text-xs text-emerald-400 font-bold">+{typeof anom30d === 'number' ? anom30d.toFixed(1) : anom30d}% vs normal</span>
          </div>
          <div className="mt-3">
            <div className="text-3xl font-black text-white">
              {typeof r30d === 'number' ? r30d.toFixed(1) : r30d} <span className="text-sm font-semibold text-slate-400">mm</span>
            </div>
            <p className="text-[11px] text-cyan-300 mt-1">CHIRPS daily accumulated series</p>
          </div>
        </Card>

        {/* Metric 4: Data Freshness */}
        <Card variant="flood">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-300 font-medium">Data Freshness</span>
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
          { key: 'trend', label: 'Rainfall Trend' },
          { key: 'geo', label: 'Geographic Context' },
          { key: 'risk', label: 'Risk Analysis' },
          { key: 'sources', label: 'Data & Sources' },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={`px-4 py-2.5 font-medium border-b-2 transition-all ${
              activeTab === tab.key
                ? 'border-cyan-400 text-cyan-300 bg-cyan-950/30'
                : 'border-transparent text-slate-400 hover:text-slate-200'
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
            <Card variant="flood">
              <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-navy-800">
                <div>
                  <h3 className="text-base font-bold text-white">Daily Rainfall — Gorakhpur</h3>
                  <p className="text-xs text-slate-400">
                    Comparing daily volume with 10-year historical baseline (CHIRPS & GPM)
                  </p>
                </div>
                <div className="flex items-center space-x-1.5 bg-navy-900 p-1 rounded-lg border border-navy-800 text-xs">
                  {(['7', '30', '90', '365'] as const).map((r) => (
                    <button
                      key={r}
                      onClick={() => setTimeRange(r)}
                      className={`px-2.5 py-0.5 rounded font-medium transition ${
                        timeRange === r
                          ? 'bg-cyan-500 text-navy-950 font-bold'
                          : 'text-slate-400 hover:text-white'
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
                  barColor="#00e5ff"
                  lineColor="#38bdf8"
                  height={250}
                />
              </div>
            </Card>
          )}

          {activeTab === 'geo' && (
            <Card variant="flood">
              <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-navy-800">
                <div className="flex items-center space-x-2">
                  <Compass className="w-4 h-4 text-cyan-400" />
                  <h3 className="text-sm font-bold text-white">Geographic Terrain Context</h3>
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
                          ? 'bg-cyan-500 text-navy-950 shadow-sm'
                          : 'bg-navy-800 text-slate-300 hover:text-white'
                      }`}
                    >
                      {layer.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="mt-3 p-4 rounded-xl bg-navy-900/80 border border-navy-800 text-xs text-slate-300 space-y-2.5">
                <div className="flex justify-between items-center py-1.5 border-b border-navy-850">
                  <span className="text-slate-400">River Basin</span>
                  <span className="font-semibold text-white">Rapti, Rohini & Ami River Drainage</span>
                </div>
                <div className="flex justify-between items-center py-1.5 border-b border-navy-850">
                  <span className="text-slate-400">Average District Elevation</span>
                  <span className="font-semibold text-white">{districtData.elevationM} m above Mean Sea Level</span>
                </div>
                <div className="flex justify-between items-center py-1.5 border-b border-navy-850">
                  <span className="text-slate-400">Terrain Slope / Inundation Susceptibility</span>
                  <span className="font-semibold text-amber-300">Gentle Terai gradient (&lt; 1.2° slope)</span>
                </div>
                <div className="flex justify-between items-center py-1.5">
                  <span className="text-slate-400">UPSDMA 2024 Profile</span>
                  <span className="font-semibold text-rose-400">Hyper-sensitive flood category</span>
                </div>
              </div>
            </Card>
          )}

          {activeTab === 'risk' && (
            <Card variant="flood">
              <h3 className="text-sm font-bold text-white pb-3 border-b border-navy-800">
                Detailed Indicator Decomposition
              </h3>
              <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-xl bg-navy-900 border border-navy-800">
                  <span className="text-slate-400 block mb-1">7-Day Rainfall Accumulation</span>
                  <span className="text-lg font-black text-rose-400">286 mm</span>
                  <p className="text-[11px] text-slate-400 mt-1">Exceeds 90th percentile historical threshold.</p>
                </div>
                <div className="p-3 rounded-xl bg-navy-900 border border-navy-800">
                  <span className="text-slate-400 block mb-1">Standardized Precipitation Index (SPI-1)</span>
                  <span className="text-lg font-black text-cyan-300">+1.45 (Extremely Wet)</span>
                  <p className="text-[11px] text-slate-400 mt-1">Indicates significant meteorological surplus.</p>
                </div>
                <div className="p-3 rounded-xl bg-navy-900 border border-navy-800">
                  <span className="text-slate-400 block mb-1">Topographic Wetness Index (TWI)</span>
                  <span className="text-lg font-black text-amber-300">High Runoff Retention</span>
                  <p className="text-[11px] text-slate-400 mt-1">SRTM DEM indicates poor natural outflow.</p>
                </div>
                <div className="p-3 rounded-xl bg-navy-900 border border-navy-800">
                  <span className="text-slate-400 block mb-1">Estimated Return Period Proxy</span>
                  <span className="text-lg font-black text-rose-400">1-in-8 Year Event</span>
                  <p className="text-[11px] text-slate-400 mt-1">Based on 1981–2024 CHIRPS distribution.</p>
                </div>
              </div>
            </Card>
          )}

          {activeTab === 'sources' && (
            <Card variant="flood">
              <h3 className="text-sm font-bold text-white pb-3 border-b border-navy-800">
                Data Provenance & Citations
              </h3>
              <div className="mt-3 space-y-2.5 text-xs text-slate-300">
                <div className="p-3 rounded-xl bg-navy-900 border border-navy-800 flex justify-between items-center">
                  <div>
                    <div className="font-bold text-white">NASA GPM IMERG 0.1° Satellite Run</div>
                    <div className="text-[11px] text-slate-400">Calibrated microwave radar estimates</div>
                  </div>
                  <span className="text-cyan-400 font-mono text-[11px]">Late Run v07B</span>
                </div>
                <div className="p-3 rounded-xl bg-navy-900 border border-navy-800 flex justify-between items-center">
                  <div>
                    <div className="font-bold text-white">CHIRPS Daily Station Blend</div>
                    <div className="text-[11px] text-slate-400">Historical precipitation baseline (1981–present)</div>
                  </div>
                  <span className="text-cyan-400 font-mono text-[11px]">UCSB CHG v2.0</span>
                </div>
                <div className="p-3 rounded-xl bg-navy-900 border border-navy-800 flex justify-between items-center">
                  <div>
                    <div className="font-bold text-white">UPSDMA State Flood Mock Exercise Report 2024</div>
                    <div className="text-[11px] text-slate-400">Official hazard profile & Rapti basin classification</div>
                  </div>
                  <span className="text-emerald-400 font-mono text-[11px]">Official Govt Doc</span>
                </div>
              </div>
            </Card>
          )}
        </div>

        {/* Right Column: Key Insights & Transparency Notes (4 cols) */}
        <div className="lg:col-span-4 space-y-4">
          <Card variant="flood">
            <h3 className="text-sm font-bold text-white pb-2 border-b border-navy-800 flex items-center space-x-2">
              <Info className="w-4 h-4 text-cyan-400" />
              <span>Key Insights</span>
            </h3>
            <ul className="mt-3 text-xs text-slate-300 space-y-2.5 leading-relaxed">
              <li className="flex items-start space-x-2">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 mt-1.5 shrink-0" />
                <span>
                  Recent 7-day rainfall ({districtData.rainfall7dMm} mm) is {districtData.anomalyPct}% higher than
                  the October historical average in eastern UP.
                </span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-400 mt-1.5 shrink-0" />
                <span>
                  Low-lying tehsils adjacent to Rapti river embankments have heightened vulnerability.
                </span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-1.5 shrink-0" />
                <span>
                  Continuous data tracking active. Use official alerts for evacuation orders.
                </span>
              </li>
            </ul>
          </Card>

          <Card className="bg-navy-900/60 border border-navy-800">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider pb-2 border-b border-navy-800">
              Scientific Transparency Note
            </h3>
            <p className="mt-2 text-xs text-slate-400 leading-relaxed">
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
