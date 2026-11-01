import React, { useState, useEffect } from 'react';
import {
  CloudRain,
  Waves,
  Sun,
  Sprout,
  ArrowRight,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Flame,
  MapPin,
  Database,
  BarChart2,
  Sparkles,
  ShieldCheck,
  Info,
  Calendar,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { Card } from '../components/common/Card';
import { DistrictRiskMap } from '../components/map/DistrictRiskMap';
import { RainfallChart, RainfallDataPoint } from '../components/charts/RainfallChart';
import { apiService, DashboardOverviewResponse, RainfallTrendsResponse } from '../services/api';
import { DataProvenanceBadge } from '../components/common/DataProvenanceBadge';
import {
  UP_DISTRICTS_DATA,
  getFilteredRainfallData,
  IS_DEMO_DATA,
  DEMO_DATA_DISCLAIMER,
} from '../data/mockData';

export const MainDashboardView: React.FC = () => {
  const {
    setCurrentRoute,
    setSelectedLocation,
    selectedLocation,
    dataFreshnessMode,
    setDataFreshnessMode,
    activeLocationData,
    isConfiguredPilot,
  } = useApp();

  const [trendRange, setTrendRange] = useState<'7' | '30' | '90' | '365'>('30');
  const [trendDistrict, setTrendDistrict] = useState<'gorakhpur' | 'mahoba'>('gorakhpur');
  const [backendDashboard, setBackendDashboard] = useState<DashboardOverviewResponse | null>(null);
  const [backendTrends, setBackendTrends] = useState<RainfallTrendsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    setIsLoading(true);
    const loc = selectedLocation === 'all' ? 'gorakhpur' : selectedLocation;
    apiService
      .fetchDashboard(loc)
      .then((data) => setBackendDashboard(data))
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, [selectedLocation]);

  useEffect(() => {
    const rangeParam = trendRange === '7' ? '7d' : trendRange === '30' ? '30d' : trendRange === '90' ? '90d' : '365d';
    apiService
      .fetchRainfallTrends(trendDistrict, rangeParam)
      .then((data) => setBackendTrends(data))
      .catch(() => {});
  }, [trendDistrict, trendRange]);

  const gorakhpurData = UP_DISTRICTS_DATA.find((d) => d.id === 'gorakhpur')!;
  const mahobaData = UP_DISTRICTS_DATA.find((d) => d.id === 'mahoba')!;

  let chartData: RainfallDataPoint[] = getFilteredRainfallData(trendDistrict, trendRange, 'daily');
  if (backendTrends?.series && backendTrends.series.length > 0) {
    chartData = backendTrends.series.map((pt) => ({
      date: pt.date,
      rainfall: pt.observed_rainfall_mm,
      historicalAvg: pt.historical_avg_mm,
    }));
  }

  return (
    <div className="space-y-6">
      {/* 0. Demo Data & State Notice Banner */}
      {dataFreshnessMode === 'error' ? (
        <div className="p-3.5 rounded-2xl bg-rose-500/20 border border-rose-500/50 flex items-center justify-between text-xs text-rose-200">
          <div className="flex items-center space-x-2.5">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>
              <strong>Simulated Feed Error:</strong> Failed to connect to geospatial ingestion stream. Demonstrating error state.
            </span>
          </div>
          <button
            onClick={() => setDataFreshnessMode('fresh')}
            className="px-2.5 py-1 rounded-lg bg-rose-500 text-white font-bold hover:bg-rose-400 transition"
          >
            Retry Connection
          </button>
        </div>
      ) : dataFreshnessMode === 'stale' ? (
        <div className="p-3.5 rounded-2xl bg-amber-500/20 border border-amber-500/50 flex items-center justify-between text-xs text-amber-200">
          <div className="flex items-center space-x-2.5">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              <strong>Stale Data Warning:</strong> Satellite telemetry is older than 24 hours. Historical baselines retained.
            </span>
          </div>
          <button
            onClick={() => setDataFreshnessMode('fresh')}
            className="px-2.5 py-1 rounded-lg bg-amber-500 text-navy-950 font-bold hover:bg-amber-400 transition"
          >
            Acknowledge
          </button>
        </div>
      ) : (
        <div className="px-3.5 py-2.5 rounded-xl bg-navy-900/60 border border-navy-800 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-400">
          <div className="flex items-center space-x-2">
            <DataProvenanceBadge
              mode={backendDashboard?.data_mode || (isConfiguredPilot ? 'CACHED_VERIFIED' : 'DATA_PENDING')}
              source="CHIRPS v2.0 & NASA GPM Late Run"
              datasetVersion="v2.0"
              spatialResolution="0.05° (~5.3 km)"
            />
            <span className="hidden sm:inline">
              <strong>Decision-Support Prototype:</strong> {DEMO_DATA_DISCLAIMER}
            </span>
          </div>
          <span className="font-mono text-cyan-400 hidden md:inline">Pilot: UP-2026</span>
        </div>
      )}

      {/* 0.1 Candidate District Isolation & Pending Telemetry Banner */}
      {!isConfiguredPilot && (
        <div className="p-4 rounded-2xl bg-navy-900/90 border border-cyan-500/30 shadow-lg space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center space-x-3">
              <div className="w-9 h-9 rounded-xl bg-cyan-500/20 border border-cyan-500/30 flex items-center justify-center text-cyan-300 shrink-0">
                <Database className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                  <span>{activeLocationData.name} {activeLocationData.hindiName ? `(${activeLocationData.hindiName})` : ''}</span>
                  <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                    Candidate District • Ingestion Pending
                  </span>
                </h3>
                <p className="text-xs text-slate-400">
                  Administrative Region: {activeLocationData.region} • Basin: {activeLocationData.riverBasin || 'Regional Basin'}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-2 text-xs">
              <button
                onClick={() => setSelectedLocation('gorakhpur')}
                className="px-2.5 py-1 rounded-lg bg-sky-500/20 text-sky-300 hover:bg-sky-500/30 border border-sky-500/40 transition font-medium text-[11px]"
              >
                Gorakhpur Flood Pilot
              </button>
              <button
                onClick={() => setSelectedLocation('mahoba')}
                className="px-2.5 py-1 rounded-lg bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 border border-amber-500/40 transition font-medium text-[11px]"
              >
                Mahoba Drought Pilot
              </button>
            </div>
          </div>
          <div className="p-3 rounded-xl bg-navy-950/80 border border-navy-800 text-xs text-slate-300 leading-relaxed">
            <strong>Scientific Integrity & Data Isolation Notice:</strong> JalRakshak AI maintains strict isolation between administrative regions. Candidate districts are registered in the spatial hierarchy (EPSG:4326), but hazard indicators and calibrated return periods will only be activated following validated station-blended telemetry ingestion. <em>This district never inherits or interpolates risk scores from Gorakhpur or Mahoba.</em>
          </div>
        </div>
      )}

      {/* 1. Hero Section with Headline & Hazard Focus Cards */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-2">
        <div className="max-w-2xl">
          <h1 className="text-3xl lg:text-4xl font-extrabold text-white tracking-tight leading-tight">
            Smarter Insights <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-sky-300">
              for Safer Communities
            </span>
          </h1>
          <p className="mt-2 text-slate-300 text-sm lg:text-base leading-relaxed">
            AI-powered flood and drought risk assessment for Uttar Pradesh pilot districts.
          </p>
        </div>

        {/* Hazard Focus Quick Launchers */}
        <div className="flex items-center gap-3">
          {/* Flood Focus Pill Button */}
          <button
            onClick={() => {
              setSelectedLocation('gorakhpur');
              setCurrentRoute('flood');
            }}
            className="flex-1 sm:flex-none flex items-center justify-between space-x-4 px-5 py-3.5 rounded-2xl bg-gradient-to-r from-sky-950/80 to-cyan-950/80 border border-cyan-400/40 hover:border-cyan-400 shadow-glow-cyan interactive-btn group"
          >
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-cyan-500/20 text-cyan-300 flex items-center justify-center">
                <Waves className="w-5 h-5 group-hover:scale-110 transition-transform" />
              </div>
              <div className="text-left">
                <div className="text-xs uppercase font-bold tracking-wider text-cyan-300">
                  Flood Focus
                </div>
                <div className="text-sm font-extrabold text-white">Gorakhpur</div>
              </div>
            </div>
            <div className="w-7 h-7 rounded-full bg-cyan-500/30 flex items-center justify-center text-cyan-200 group-hover:translate-x-1 transition-transform">
              <ChevronRight className="w-4 h-4" />
            </div>
          </button>

          {/* Drought Focus Pill Button */}
          <button
            onClick={() => {
              setSelectedLocation('mahoba');
              setCurrentRoute('drought');
            }}
            className="flex-1 sm:flex-none flex items-center justify-between space-x-4 px-5 py-3.5 rounded-2xl bg-gradient-to-r from-amber-950/80 to-orange-950/80 border border-amber-400/40 hover:border-amber-400 shadow-glow-amber interactive-btn group"
          >
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-amber-500/20 text-amber-300 flex items-center justify-center">
                <Sun className="w-5 h-5 group-hover:scale-110 transition-transform" />
              </div>
              <div className="text-left">
                <div className="text-xs uppercase font-bold tracking-wider text-amber-300">
                  Drought Focus
                </div>
                <div className="text-sm font-extrabold text-white">Mahoba</div>
              </div>
            </div>
            <div className="w-7 h-7 rounded-full bg-amber-500/30 flex items-center justify-center text-amber-200 group-hover:translate-x-1 transition-transform">
              <ChevronRight className="w-4 h-4" />
            </div>
          </button>
        </div>
      </div>

      {/* 2. Top Metric Cards Row (4 cards matching the approved mockup or candidate pending states) */}
      {!isConfiguredPilot ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card variant="default" className="relative overflow-hidden group">
            <div className="flex items-start justify-between">
              <div className="w-11 h-11 rounded-xl bg-slate-800 text-slate-400 flex items-center justify-center">
                <CloudRain className="w-6 h-6" />
              </div>
              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                Data Pending
              </span>
            </div>
            <div className="mt-4">
              <p className="text-xs text-slate-400 font-medium">Current Rainfall</p>
              <p className="text-xs font-semibold text-slate-200">{activeLocationData.name}</p>
              <div className="mt-1 flex items-baseline space-x-2">
                <span className="text-3xl font-extrabold text-slate-400 tracking-tight">--</span>
                <span className="text-sm font-semibold text-slate-500">mm</span>
              </div>
              <p className="mt-2 text-xs text-slate-400">Station telemetry stream unlinked</p>
            </div>
          </Card>

          <Card variant="default" className="relative overflow-hidden group">
            <div className="flex items-start justify-between">
              <div className="w-11 h-11 rounded-xl bg-slate-800 text-slate-400 flex items-center justify-center">
                <Waves className="w-6 h-6" />
              </div>
              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                Data Pending
              </span>
            </div>
            <div className="mt-4">
              <p className="text-xs text-slate-400 font-medium">7-Day Cumulative</p>
              <p className="text-xs font-semibold text-slate-200">{activeLocationData.name}</p>
              <div className="mt-1 flex items-baseline space-x-2">
                <span className="text-3xl font-extrabold text-slate-400 tracking-tight">--</span>
                <span className="text-sm font-semibold text-slate-500">mm</span>
              </div>
              <p className="mt-2 text-xs text-slate-400">Ingestion pipeline awaiting execution</p>
            </div>
          </Card>

          <Card variant="default" className="relative overflow-hidden group">
            <div className="flex items-start justify-between">
              <div className="w-11 h-11 rounded-xl bg-slate-800 text-slate-400 flex items-center justify-center">
                <Sun className="w-6 h-6" />
              </div>
              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                Pending Baseline
              </span>
            </div>
            <div className="mt-4">
              <p className="text-xs text-slate-400 font-medium">Seasonal Normal</p>
              <p className="text-xs font-semibold text-slate-200">{activeLocationData.name}</p>
              <div className="mt-1 flex items-baseline space-x-2">
                <span className="text-3xl font-extrabold text-slate-400 tracking-tight">--</span>
                <span className="text-sm font-semibold text-slate-500">mm</span>
              </div>
              <p className="mt-2 text-xs text-slate-400">30-year climatology uncalibrated</p>
            </div>
          </Card>

          <Card variant="default" className="relative overflow-hidden group">
            <div className="flex items-start justify-between">
              <div className="w-11 h-11 rounded-xl bg-slate-800 text-slate-400 flex items-center justify-center">
                <Sprout className="w-6 h-6" />
              </div>
              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                Model Offline
              </span>
            </div>
            <div className="mt-4">
              <p className="text-xs text-slate-400 font-medium">Hazard Status</p>
              <p className="text-xs font-semibold text-slate-200">{activeLocationData.name}</p>
              <div className="mt-1 flex items-baseline space-x-2">
                <span className="text-2xl font-extrabold text-slate-400 tracking-tight">Pending</span>
              </div>
              <p className="mt-2 text-xs text-slate-400">Zero data bleed from pilot models</p>
            </div>
          </Card>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: Gorakhpur Current Rainfall */}
          <Card
            variant="flood"
            hoverEffect
            onClick={() => {
              setSelectedLocation('gorakhpur');
              setCurrentRoute('flood');
            }}
            className="relative overflow-hidden group"
          >
            <div className="flex items-start justify-between">
              <div className="w-11 h-11 rounded-xl bg-cyan-500/15 border border-cyan-500/30 text-cyan-300 flex items-center justify-center shadow-inner">
                <CloudRain className="w-6 h-6" />
              </div>
              <button
                className="w-7 h-7 rounded-full bg-cyan-500/20 text-cyan-300 flex items-center justify-center group-hover:bg-cyan-500 group-hover:text-white transition-all"
                aria-label="View Gorakhpur Current Rainfall"
              >
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="mt-4">
              <p className="text-xs text-slate-400 font-medium">Current Rainfall</p>
              <p className="text-xs font-semibold text-cyan-300">Gorakhpur</p>
              <div className="mt-1 flex items-baseline space-x-2">
                <span className="text-3xl font-extrabold text-white tracking-tight">
                  {gorakhpurData.rainfall7dMm}
                </span>
                <span className="text-sm font-semibold text-slate-300">mm</span>
              </div>
              <div className="mt-2 flex items-center text-xs font-bold text-emerald-400">
                <TrendingUp className="w-3.5 h-3.5 mr-1" />
                <span>+{gorakhpurData.anomalyPct}% vs normal</span>
              </div>
            </div>
          </Card>

          {/* Card 2: Gorakhpur 7-Day Rainfall */}
          <Card
            variant="flood"
            hoverEffect
            onClick={() => {
              setSelectedLocation('gorakhpur');
              setCurrentRoute('flood');
            }}
            className="relative overflow-hidden group"
          >
            <div className="flex items-start justify-between">
              <div className="w-11 h-11 rounded-xl bg-sky-500/15 border border-sky-500/30 text-sky-300 flex items-center justify-center shadow-inner">
                <Waves className="w-6 h-6" />
              </div>
              <button
                className="w-7 h-7 rounded-full bg-sky-500/20 text-sky-300 flex items-center justify-center group-hover:bg-sky-500 group-hover:text-white transition-all"
                aria-label="View Gorakhpur 7-Day Rainfall"
              >
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="mt-4">
              <p className="text-xs text-slate-400 font-medium">7-Day Rainfall</p>
              <p className="text-xs font-semibold text-sky-300">Gorakhpur</p>
              <div className="mt-1 flex items-baseline space-x-2">
                <span className="text-3xl font-extrabold text-white tracking-tight">
                  {gorakhpurData.rainfall30dMm}
                </span>
                <span className="text-sm font-semibold text-slate-300">mm</span>
              </div>
              <div className="mt-2 flex items-center text-xs font-bold text-emerald-400">
                <TrendingUp className="w-3.5 h-3.5 mr-1" />
                <span>+48% vs normal</span>
              </div>
            </div>
          </Card>

          {/* Card 3: Mahoba 90-Day Rainfall */}
          <Card
            variant="drought"
            hoverEffect
            onClick={() => {
              setSelectedLocation('mahoba');
              setCurrentRoute('drought');
            }}
            className="relative overflow-hidden group"
          >
            <div className="flex items-start justify-between">
              <div className="w-11 h-11 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-300 flex items-center justify-center shadow-inner">
                <Sun className="w-6 h-6" />
              </div>
              <button
                className="w-7 h-7 rounded-full bg-amber-500/20 text-amber-300 flex items-center justify-center group-hover:bg-amber-500 group-hover:text-white transition-all"
                aria-label="View Mahoba 90-Day Rainfall"
              >
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="mt-4">
              <p className="text-xs text-slate-400 font-medium">90-Day Rainfall</p>
              <p className="text-xs font-semibold text-amber-300">Mahoba</p>
              <div className="mt-1 flex items-baseline space-x-2">
                <span className="text-3xl font-extrabold text-white tracking-tight">
                  {mahobaData.rainfall90dMm}
                </span>
                <span className="text-sm font-semibold text-slate-300">mm</span>
              </div>
              <div className="mt-2 flex items-center text-xs font-bold text-rose-400">
                <TrendingDown className="w-3.5 h-3.5 mr-1" />
                <span>{mahobaData.anomalyPct}% vs normal</span>
              </div>
            </div>
          </Card>

          {/* Card 4: Mahoba Seasonal Deficit */}
          <Card
            variant="drought"
            hoverEffect
            onClick={() => {
              setSelectedLocation('mahoba');
              setCurrentRoute('drought');
            }}
            className="relative overflow-hidden group"
          >
            <div className="flex items-start justify-between">
              <div className="w-11 h-11 rounded-xl bg-orange-500/15 border border-orange-500/30 text-orange-300 flex items-center justify-center shadow-inner">
                <Sprout className="w-6 h-6" />
              </div>
              <button
                className="w-7 h-7 rounded-full bg-orange-500/20 text-orange-300 flex items-center justify-center group-hover:bg-orange-500 group-hover:text-white transition-all"
                aria-label="View Mahoba Seasonal Deficit"
              >
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="mt-4">
              <p className="text-xs text-slate-400 font-medium">Seasonal Deficit</p>
              <p className="text-xs font-semibold text-orange-300">Mahoba</p>
              <div className="mt-1 flex items-baseline space-x-2">
                <span className="text-3xl font-extrabold text-rose-400 tracking-tight">
                  {mahobaData.seasonalDeficitPct}%
                </span>
              </div>
              <div className="mt-2 flex items-center text-xs font-semibold text-amber-300">
                <span>Severe Bundelkhand deficit</span>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* 3. Main Operational Intelligence Grid (Map, Trends, Sidebar Columns) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Risk Map Overview (5 cols) */}
        <div className="lg:col-span-5 flex flex-col">
          <Card className="flex-1 flex flex-col justify-between">
            <div className="flex items-center justify-between pb-3 border-b border-navy-800">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-lg bg-cyan-500/20 text-cyan-300 flex items-center justify-center">
                  <MapPin className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Risk Map Overview</h3>
                  <p className="text-[11px] text-slate-400">Uttar Pradesh pilot zones</p>
                </div>
              </div>

              <select
                value={selectedLocation}
                onChange={(e) => setSelectedLocation(e.target.value as any)}
                className="bg-navy-850 border border-navy-700 text-xs text-slate-200 rounded-lg px-2.5 py-1 focus:outline-none focus:border-cyan-400"
              >
                <option value="all">Uttar Pradesh (All)</option>
                <option value="gorakhpur">Gorakhpur</option>
                <option value="mahoba">Mahoba</option>
              </select>
            </div>

            {/* Map render container */}
            <div className="my-3 flex-1 min-h-[310px]">
              <DistrictRiskMap />
            </div>
          </Card>
        </div>

        {/* Center Column: Recent Rainfall Trend (4 cols) */}
        <div className="lg:col-span-4 flex flex-col">
          <Card className="flex-1 flex flex-col justify-between">
            <div>
              {/* Header with District Switcher */}
              <div className="flex items-center justify-between pb-3 border-b border-navy-800">
                <div className="flex items-center space-x-2">
                  <Calendar className="w-4 h-4 text-cyan-400" />
                  <h3 className="text-sm font-bold text-white">Recent Rainfall Trend</h3>
                </div>
                <select
                  value={trendDistrict}
                  onChange={(e) => setTrendDistrict(e.target.value as any)}
                  className="bg-navy-850 border border-navy-700 text-xs text-slate-200 rounded-lg px-2 py-1 focus:outline-none focus:border-cyan-400"
                >
                  <option value="gorakhpur">Gorakhpur</option>
                  <option value="mahoba">Mahoba</option>
                </select>
              </div>

              {/* Range Selector Pills */}
              <div className="flex items-center gap-1.5 mt-3 p-1 rounded-xl bg-navy-900 border border-navy-800 text-xs">
                {(
                  [
                    { key: '7', label: '7 Days' },
                    { key: '30', label: '30 Days' },
                    { key: '90', label: '90 Days' },
                    { key: '365', label: '1 Year' },
                  ] as const
                ).map((range) => (
                  <button
                    key={range.key}
                    onClick={() => setTrendRange(range.key)}
                    className={`flex-1 py-1 text-center font-medium rounded-lg transition-all ${
                      trendRange === range.key
                        ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    {range.label}
                  </button>
                ))}
              </div>

              {/* Chart Component */}
              <div className="mt-4">
                {!isConfiguredPilot ? (
                  <div className="p-6 rounded-2xl bg-navy-900/80 border border-navy-800 text-center space-y-3">
                    <div className="w-10 h-10 mx-auto rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center">
                      <Database className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-white">
                        No Historical Telemetry Ingested for {activeLocationData.name}
                      </h4>
                      <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                        Daily precipitation series pending onboarding into partition table. JalRakshak integrity rules strictly prevent proxy interpolation from Gorakhpur or Mahoba.
                      </p>
                    </div>
                    <div className="flex items-center justify-center gap-2 pt-1">
                      <button
                        onClick={() => {
                          setSelectedLocation('gorakhpur');
                          setTrendDistrict('gorakhpur');
                        }}
                        className="px-2.5 py-1 rounded-lg bg-sky-500/20 text-sky-300 hover:bg-sky-500/30 border border-sky-500/40 text-[11px] font-semibold transition"
                      >
                        View Gorakhpur Series
                      </button>
                      <button
                        onClick={() => {
                          setSelectedLocation('mahoba');
                          setTrendDistrict('mahoba');
                        }}
                        className="px-2.5 py-1 rounded-lg bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 border border-amber-500/40 text-[11px] font-semibold transition"
                      >
                        View Mahoba Series
                      </button>
                    </div>
                  </div>
                ) : (
                  <RainfallChart
                    data={chartData}
                    barColor={trendDistrict === 'gorakhpur' ? '#00e5ff' : '#f59e0b'}
                    lineColor="#38bdf8"
                    height={190}
                  />
                )}
              </div>
            </div>

            {/* Key Insights bullets */}
            <div className="mt-4 pt-3 border-t border-navy-800 space-y-2">
              <div className="text-xs font-bold text-slate-300 flex items-center space-x-1.5">
                <Info className="w-3.5 h-3.5 text-cyan-400" />
                <span>Key Insights</span>
              </div>
              <ul className="text-xs text-slate-300 space-y-1.5">
                <li className="flex items-start space-x-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 mt-1.5 shrink-0" />
                  <span>
                    {!isConfiguredPilot
                      ? `Observational pipeline for ${activeLocationData.name} (${activeLocationData.region}) is awaiting ingestion.`
                      : trendDistrict === 'gorakhpur'
                      ? 'Recent rainfall is significantly higher than historical average for this period.'
                      : 'Accumulated precipitation is 58% below 10-year seasonal median.'}
                  </span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-1.5 shrink-0" />
                  <span>
                    {!isConfiguredPilot
                      ? 'Zero data bleed: candidate districts do not inherit telemetry or hazard models from pilot zones.'
                      : trendDistrict === 'gorakhpur'
                      ? 'Low-lying areas near Rapti river may be more vulnerable.'
                      : 'Soil moisture depletion indicates emerging agricultural stress in Bundelkhand.'}
                  </span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-1.5 shrink-0" />
                  <span>
                    {!isConfiguredPilot
                      ? 'Hydrological and meteorological risk baselines are unconfigured until station observations are verified.'
                      : 'Continuous monitoring is recommended. Decision-support prototype.'}
                  </span>
                </li>
              </ul>
            </div>
          </Card>
        </div>

        {/* Right Column: Alerts, Key Locations, Data Sources (3 cols) */}
        <div className="lg:col-span-3 space-y-4">
          {/* Card 1: Alert & Updates */}
          <Card className="p-4">
            <div className="flex items-center justify-between pb-2 border-b border-navy-800">
              <h3 className="text-xs font-bold text-white flex items-center space-x-1.5">
                <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
                <span>Alert & Updates</span>
              </h3>
              <button
                onClick={() => setCurrentRoute('monitoring')}
                className="text-[11px] text-cyan-400 hover:underline flex items-center"
              >
                View All <ChevronRight className="w-3 h-3" />
              </button>
            </div>
            <div className="mt-3 space-y-2.5">
              <div
                onClick={() => {
                  setSelectedLocation('gorakhpur');
                  setCurrentRoute('flood');
                }}
                className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/25 hover:border-rose-500/50 cursor-pointer transition"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-rose-300">High Rainfall Alert</span>
                  <span className="text-[10px] text-rose-400 font-mono">Gorakhpur</span>
                </div>
                <p className="text-[11px] text-slate-300 mt-0.5 leading-snug">
                  Recent rainfall significantly above historical average.
                </p>
              </div>

              <div
                onClick={() => {
                  setSelectedLocation('mahoba');
                  setCurrentRoute('drought');
                }}
                className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/25 hover:border-amber-500/50 cursor-pointer transition"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-amber-300">Drought Watch</span>
                  <span className="text-[10px] text-amber-400 font-mono">Mahoba</span>
                </div>
                <p className="text-[11px] text-slate-300 mt-0.5 leading-snug">
                  Rainfall below historical average for the season.
                </p>
              </div>
            </div>
          </Card>

          {/* Card 2: Key Locations */}
          <Card className="p-4">
            <div className="flex items-center justify-between pb-2 border-b border-navy-800">
              <h3 className="text-xs font-bold text-white flex items-center space-x-1.5">
                <MapPin className="w-3.5 h-3.5 text-cyan-400" />
                <span>Key Locations</span>
              </h3>
              <button
                onClick={() => setCurrentRoute('map')}
                className="text-[11px] text-cyan-400 hover:underline flex items-center"
              >
                View All <ChevronRight className="w-3 h-3" />
              </button>
            </div>
            <div className="mt-3 space-y-2">
              <div
                onClick={() => {
                  setSelectedLocation('gorakhpur');
                  setCurrentRoute('flood');
                }}
                className="p-2 rounded-xl bg-navy-850/60 hover:bg-navy-800 border border-navy-700/60 flex items-center justify-between cursor-pointer transition"
              >
                <div className="flex items-center space-x-2.5">
                  <div className="w-7 h-7 rounded-lg bg-sky-500/20 text-sky-400 flex items-center justify-center">
                    <MapPin className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-white">Gorakhpur</div>
                    <div className="text-[10px] text-slate-400 font-mono">26.7606° N, 83.3732° E</div>
                  </div>
                </div>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                  Flood Focus
                </span>
              </div>

              <div
                onClick={() => {
                  setSelectedLocation('mahoba');
                  setCurrentRoute('drought');
                }}
                className="p-2 rounded-xl bg-navy-850/60 hover:bg-navy-800 border border-navy-700/60 flex items-center justify-between cursor-pointer transition"
              >
                <div className="flex items-center space-x-2.5">
                  <div className="w-7 h-7 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center">
                    <MapPin className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-white">Mahoba</div>
                    <div className="text-[10px] text-slate-400 font-mono">25.2953° N, 79.8630° E</div>
                  </div>
                </div>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30">
                  Drought Focus
                </span>
              </div>
            </div>
          </Card>

          {/* Card 3: Data Sources */}
          <Card className="p-4">
            <div className="flex items-center justify-between pb-2 border-b border-navy-800">
              <h3 className="text-xs font-bold text-white flex items-center space-x-1.5">
                <Database className="w-3.5 h-3.5 text-cyan-400" />
                <span>Data Sources</span>
              </h3>
              <button
                onClick={() => setCurrentRoute('sources')}
                className="text-[11px] text-cyan-400 hover:underline flex items-center"
              >
                View All <ChevronRight className="w-3 h-3" />
              </button>
            </div>
            <div className="mt-3 space-y-1.5 text-xs text-slate-300">
              <div className="flex items-center justify-between p-1.5 rounded-lg bg-navy-900/60">
                <span className="font-semibold text-white">NASA GPM IMERG</span>
                <span className="text-[10px] text-slate-400">0.1° Gridded Sat</span>
              </div>
              <div className="flex items-center justify-between p-1.5 rounded-lg bg-navy-900/60">
                <span className="font-semibold text-white">CHIRPS Daily</span>
                <span className="text-[10px] text-slate-400">1981–Present</span>
              </div>
              <div className="flex items-center justify-between p-1.5 rounded-lg bg-navy-900/60">
                <span className="font-semibold text-white">SRTM DEM</span>
                <span className="text-[10px] text-slate-400">30m Elevation</span>
              </div>
              <div className="flex items-center justify-between p-1.5 rounded-lg bg-navy-900/60">
                <span className="font-semibold text-white">UPSDMA / IMD</span>
                <span className="text-[10px] text-emerald-400">Official Warning Links</span>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* 4. Bottom Row Action Shortcuts (4 cards matching the approved mockup) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-2">
        <button
          onClick={() => setCurrentRoute('trends')}
          className="flex items-center justify-between p-4 rounded-2xl glass-panel hover:glass-panel-flood interactive-btn text-left group"
        >
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/20 text-cyan-300 flex items-center justify-center">
              <BarChart2 className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-bold text-white group-hover:text-cyan-300 transition-colors">
                Rainfall & Trends
              </div>
              <div className="text-xs text-slate-400">Historical analysis</div>
            </div>
          </div>
          <ChevronRight className="w-5 h-5 text-slate-500 group-hover:text-cyan-400 group-hover:translate-x-1 transition-all" />
        </button>

        <button
          onClick={() => setCurrentRoute('assistant')}
          className="flex items-center justify-between p-4 rounded-2xl glass-panel hover:glass-panel-flood interactive-btn text-left group"
        >
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-sky-500/20 text-sky-300 flex items-center justify-center">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-bold text-white group-hover:text-sky-300 transition-colors">
                AI Assistant
              </div>
              <div className="text-xs text-slate-400">Ask questions</div>
            </div>
          </div>
          <ChevronRight className="w-5 h-5 text-slate-500 group-hover:text-sky-400 group-hover:translate-x-1 transition-all" />
        </button>

        <button
          onClick={() => setCurrentRoute('preparedness')}
          className="flex items-center justify-between p-4 rounded-2xl glass-panel hover:border-emerald-500/40 interactive-btn text-left group"
        >
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/20 text-emerald-300 flex items-center justify-center">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-bold text-white group-hover:text-emerald-300 transition-colors">
                Preparedness
              </div>
              <div className="text-xs text-slate-400">Safety guidelines</div>
            </div>
          </div>
          <ChevronRight className="w-5 h-5 text-slate-500 group-hover:text-emerald-400 group-hover:translate-x-1 transition-all" />
        </button>

        <button
          onClick={() => setCurrentRoute('sources')}
          className="flex items-center justify-between p-4 rounded-2xl glass-panel hover:border-amber-500/40 interactive-btn text-left group"
        >
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/20 text-amber-300 flex items-center justify-center">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-bold text-white group-hover:text-amber-300 transition-colors">
                Data Sources
              </div>
              <div className="text-xs text-slate-400">Transparent data</div>
            </div>
          </div>
          <ChevronRight className="w-5 h-5 text-slate-500 group-hover:text-amber-400 group-hover:translate-x-1 transition-all" />
        </button>
      </div>
    </div>
  );
};
