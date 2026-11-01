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
  MapPin,
  Database,
  BarChart2,
  Sparkles,
  ShieldCheck,
  Info,
  Calendar,
  AlertCircle,
  RefreshCw,
  Activity,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { Card } from '../components/common/Card';
import { DistrictRiskMap } from '../components/map/DistrictRiskMap';
import { RainfallChart, RainfallDataPoint } from '../components/charts/RainfallChart';
import { apiService, DashboardOverviewResponse, RainfallTrendsResponse, EnvironmentalLiveResponse } from '../services/api';
import { DataProvenanceBadge } from '../components/common/DataProvenanceBadge';
import {
  UP_DISTRICTS_DATA,
  getFilteredRainfallData,
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
  const [liveEnvironmental, setLiveEnvironmental] = useState<EnvironmentalLiveResponse | null>(null);
  const [isRefreshingLive, setIsRefreshingLive] = useState(false);
  const [liveRefreshMsg, setLiveRefreshMsg] = useState<string | null>(null);
  const [, setIsLoading] = useState(false);

  useEffect(() => {
    setIsLoading(true);
    const loc = selectedLocation === 'all' ? 'gorakhpur' : selectedLocation;
    apiService
      .fetchDashboard(loc)
      .then((data) => setBackendDashboard(data))
      .catch(() => {})
      .finally(() => setIsLoading(false));

    apiService
      .fetchEnvironmentalLive(loc)
      .then((data) => setLiveEnvironmental(data))
      .catch(() => {});
  }, [selectedLocation]);

  const handleRefreshLive = async () => {
    if (isRefreshingLive) return;
    setIsRefreshingLive(true);
    setLiveRefreshMsg(null);
    try {
      const loc = selectedLocation === 'all' ? 'gorakhpur' : selectedLocation;
      const res = await apiService.refreshEnvironmentalData(loc);
      setLiveRefreshMsg(res.message);
      const updated = await apiService.fetchEnvironmentalLive(loc);
      setLiveEnvironmental(updated);
    } catch (err: any) {
      setLiveRefreshMsg(err?.message || 'Refresh failed');
    } finally {
      setIsRefreshingLive(false);
    }
  };

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
        <div className="p-3.5 rounded-2xl bg-rose-50 border border-rose-200 flex items-center justify-between text-xs text-rose-800 shadow-sm">
          <div className="flex items-center space-x-2.5">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>
              <strong>Simulated Feed Error:</strong> Failed to connect to geospatial ingestion stream. Demonstrating error state.
            </span>
          </div>
          <button
            onClick={() => setDataFreshnessMode('fresh')}
            className="px-2.5 py-1 rounded-lg bg-rose-600 text-white font-bold hover:bg-rose-700 transition"
          >
            Retry Connection
          </button>
        </div>
      ) : dataFreshnessMode === 'stale' ? (
        <div className="p-3.5 rounded-2xl bg-amber-50 border border-amber-200 flex items-center justify-between text-xs text-amber-900 shadow-sm">
          <div className="flex items-center space-x-2.5">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            <span>
              <strong>Stale Data Warning:</strong> Satellite telemetry is older than 24 hours. Historical baselines retained.
            </span>
          </div>
          <button
            onClick={() => setDataFreshnessMode('fresh')}
            className="px-2.5 py-1 rounded-lg bg-amber-600 text-white font-bold hover:bg-amber-700 transition"
          >
            Acknowledge
          </button>
        </div>
      ) : (
        <div className="px-3.5 py-2.5 rounded-xl bg-white border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-600">
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
          <span className="font-mono text-blue-700 font-semibold hidden md:inline">Pilot: UP-2026</span>
        </div>
      )}

      {/* 0.1 Candidate District Isolation & Pending Telemetry Banner */}
      {!isConfiguredPilot && (
        <div className="p-4 rounded-2xl bg-white border border-blue-200 shadow-sm space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center space-x-3">
              <div className="w-9 h-9 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 shrink-0">
                <Database className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                  <span>{activeLocationData.name} {activeLocationData.hindiName ? `(${activeLocationData.hindiName})` : ''}</span>
                  <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                    Candidate District • Ingestion Pending
                  </span>
                </h3>
                <p className="text-xs text-slate-500">
                  Administrative Region: {activeLocationData.region} • Basin: {activeLocationData.riverBasin || 'Regional Basin'}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-2 text-xs">
              <button
                onClick={() => setSelectedLocation('gorakhpur')}
                className="px-2.5 py-1 rounded-lg bg-sky-50 text-sky-700 hover:bg-sky-100 border border-sky-200 transition font-medium text-[11px]"
              >
                Gorakhpur Flood Pilot
              </button>
              <button
                onClick={() => setSelectedLocation('mahoba')}
                className="px-2.5 py-1 rounded-lg bg-amber-50 text-amber-800 hover:bg-amber-100 border border-amber-200 transition font-medium text-[11px]"
              >
                Mahoba Drought Pilot
              </button>
            </div>
          </div>
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700 leading-relaxed">
            <strong>Scientific Integrity & Data Isolation Notice:</strong> JalRakshak AI maintains strict isolation between administrative regions. Candidate districts are registered in the spatial hierarchy (EPSG:4326), but hazard indicators and calibrated return periods will only be activated following validated station-blended telemetry ingestion. <em>This district never inherits or interpolates risk scores from Gorakhpur or Mahoba.</em>
          </div>
        </div>
      )}

      {/* 1. Operational Overview Header & Hazard Quick Launchers */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-1 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-bold uppercase tracking-wider text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
              Operations Center
            </span>
            <span className="text-xs text-slate-500 font-mono">Uttar Pradesh Agro-Hydrology</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-extrabold text-slate-900 tracking-tight mt-1">
            Smarter Insights <span className="text-blue-700">for Safer Communities</span>
          </h1>
          <p className="text-xs text-slate-600 mt-0.5">
            AI-powered flood and drought risk assessment for Uttar Pradesh pilot districts.
          </p>
        </div>

        {/* Hazard Focus Quick Launchers */}
        <div className="flex items-center gap-2.5">
          {/* Flood Focus Pill Button */}
          <button
            onClick={() => {
              setSelectedLocation('gorakhpur');
              setCurrentRoute('flood');
            }}
            className="flex items-center space-x-3 px-4 py-2.5 rounded-xl bg-white border border-slate-200 hover:border-blue-400 shadow-xs interactive-btn group"
            title="Focus Gorakhpur Flood Pilot"
          >
            <div className="w-8 h-8 rounded-lg bg-sky-50 border border-sky-100 text-sky-700 flex items-center justify-center shrink-0">
              <Waves className="w-4 h-4" />
            </div>
            <div className="text-left">
              <div className="text-[10px] uppercase font-bold tracking-wider text-sky-700">
                Flood Focus
              </div>
              <div className="text-xs font-bold text-slate-900">Gorakhpur</div>
            </div>
            <div className="w-5 h-5 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 group-hover:text-blue-600 group-hover:translate-x-0.5 transition-all">
              <ChevronRight className="w-3.5 h-3.5" />
            </div>
          </button>

          {/* Drought Focus Pill Button */}
          <button
            onClick={() => {
              setSelectedLocation('mahoba');
              setCurrentRoute('drought');
            }}
            className="flex items-center space-x-3 px-4 py-2.5 rounded-xl bg-white border border-slate-200 hover:border-amber-400 shadow-xs interactive-btn group"
            title="Focus Mahoba Drought Pilot"
          >
            <div className="w-8 h-8 rounded-lg bg-amber-50 border border-amber-100 text-amber-700 flex items-center justify-center shrink-0">
              <Sun className="w-4 h-4" />
            </div>
            <div className="text-left">
              <div className="text-[10px] uppercase font-bold tracking-wider text-amber-700">
                Drought Focus
              </div>
              <div className="text-xs font-bold text-slate-900">Mahoba</div>
            </div>
            <div className="w-5 h-5 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 group-hover:text-amber-600 group-hover:translate-x-0.5 transition-all">
              <ChevronRight className="w-3.5 h-3.5" />
            </div>
          </button>
        </div>
      </div>

      {/* 1.5 Live Environmental Data Telemetry Bar */}
      {liveEnvironmental && (
        <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start md:items-center space-x-3.5">
            <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 shrink-0 mt-0.5 md:mt-0">
              <Activity className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-bold text-sm text-slate-900">
                  Live Environmental NWP Telemetry: {liveEnvironmental.district_name}
                </span>
                <DataProvenanceBadge
                  mode={liveEnvironmental.data_mode}
                  source={liveEnvironmental.model_name}
                  datasetVersion="Open-Meteo CC-BY 4.0"
                  spatialResolution={liveEnvironmental.spatial_representation === 'representative_point_estimate' ? 'Representative Point at Centroid' : 'Gridded'}
                  lastUpdated={liveEnvironmental.freshness.retrieval_timestamp.split('T')[0]}
                  compact={true}
                />
              </div>
              <p className="text-xs text-slate-600 mt-0.5">
                {liveEnvironmental.current_conditions ? (
                  <span>
                    <strong>Current Conditions:</strong> {liveEnvironmental.current_conditions.condition_summary} •{' '}
                    <span>{liveEnvironmental.attribution}</span>
                  </span>
                ) : (
                  <span>
                    Centroid coordinates ({liveEnvironmental.coordinates.lat.toFixed(4)}°N, {liveEnvironmental.coordinates.lng.toFixed(4)}°E) •{' '}
                    <span className="text-slate-500">{liveEnvironmental.provider_status?.message || 'Awaiting live telemetry activation'}</span>
                  </span>
                )}
              </p>
              <p className="text-[11px] text-slate-500 italic mt-0.5">
                {liveEnvironmental.spatial_disclaimer}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-end md:self-center shrink-0">
            {liveRefreshMsg && (
              <span className="text-[11px] text-blue-700 font-mono hidden lg:inline">
                {liveRefreshMsg}
              </span>
            )}
            <button
              onClick={handleRefreshLive}
              disabled={isRefreshingLive}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-300 text-xs font-semibold transition disabled:opacity-50 cursor-pointer"
              title="Trigger on-demand fetch from Open-Meteo"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshingLive ? 'animate-spin text-blue-600' : ''}`} />
              <span>{isRefreshingLive ? 'Refreshing...' : 'Refresh Live'}</span>
            </button>
          </div>
        </div>
      )}

      {/* 2. Top Metric Cards Row (4 cards matching the approved mockup or candidate pending states) */}
      {!isConfiguredPilot ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card variant="default" className="relative overflow-hidden group">
            <div className="flex items-start justify-between">
              <div className="w-11 h-11 rounded-xl bg-slate-100 text-slate-500 flex items-center justify-center">
                <CloudRain className="w-6 h-6" />
              </div>
              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                Data Pending
              </span>
            </div>
            <div className="mt-4">
              <p className="text-xs text-slate-500 font-medium">Current Rainfall</p>
              <p className="text-xs font-semibold text-slate-700">{activeLocationData.name}</p>
              <div className="mt-1 flex items-baseline space-x-2">
                <span className="text-3xl font-extrabold text-slate-400 tracking-tight">--</span>
                <span className="text-sm font-semibold text-slate-400">mm</span>
              </div>
              <p className="mt-2 text-xs text-slate-500">Station telemetry stream unlinked</p>
            </div>
          </Card>

          <Card variant="default" className="relative overflow-hidden group">
            <div className="flex items-start justify-between">
              <div className="w-11 h-11 rounded-xl bg-slate-100 text-slate-500 flex items-center justify-center">
                <Waves className="w-6 h-6" />
              </div>
              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                Data Pending
              </span>
            </div>
            <div className="mt-4">
              <p className="text-xs text-slate-500 font-medium">7-Day Cumulative</p>
              <p className="text-xs font-semibold text-slate-700">{activeLocationData.name}</p>
              <div className="mt-1 flex items-baseline space-x-2">
                <span className="text-3xl font-extrabold text-slate-400 tracking-tight">--</span>
                <span className="text-sm font-semibold text-slate-400">mm</span>
              </div>
              <p className="mt-2 text-xs text-slate-500">Ingestion pipeline awaiting execution</p>
            </div>
          </Card>

          <Card variant="default" className="relative overflow-hidden group">
            <div className="flex items-start justify-between">
              <div className="w-11 h-11 rounded-xl bg-slate-100 text-slate-500 flex items-center justify-center">
                <Sun className="w-6 h-6" />
              </div>
              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                Pending Baseline
              </span>
            </div>
            <div className="mt-4">
              <p className="text-xs text-slate-500 font-medium">Seasonal Normal</p>
              <p className="text-xs font-semibold text-slate-700">{activeLocationData.name}</p>
              <div className="mt-1 flex items-baseline space-x-2">
                <span className="text-3xl font-extrabold text-slate-400 tracking-tight">--</span>
                <span className="text-sm font-semibold text-slate-400">mm</span>
              </div>
              <p className="mt-2 text-xs text-slate-500">30-year climatology uncalibrated</p>
            </div>
          </Card>

          <Card variant="default" className="relative overflow-hidden group">
            <div className="flex items-start justify-between">
              <div className="w-11 h-11 rounded-xl bg-slate-100 text-slate-500 flex items-center justify-center">
                <Sprout className="w-6 h-6" />
              </div>
              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                Model Offline
              </span>
            </div>
            <div className="mt-4">
              <p className="text-xs text-slate-500 font-medium">Hazard Status</p>
              <p className="text-xs font-semibold text-slate-700">{activeLocationData.name}</p>
              <div className="mt-1 flex items-baseline space-x-2">
                <span className="text-2xl font-extrabold text-slate-400 tracking-tight">Pending</span>
              </div>
              <p className="mt-2 text-xs text-slate-500">Zero data bleed from pilot models</p>
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
              <div className="w-11 h-11 rounded-xl bg-sky-100 text-sky-700 flex items-center justify-center">
                <CloudRain className="w-6 h-6" />
              </div>
              <button
                className="w-7 h-7 rounded-full bg-sky-100 text-sky-700 flex items-center justify-center group-hover:bg-sky-600 group-hover:text-white transition-all"
                aria-label="View Gorakhpur Current Rainfall"
              >
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="mt-4">
              <p className="text-xs text-slate-500 font-medium">Current Rainfall</p>
              <p className="text-xs font-semibold text-sky-700">Gorakhpur</p>
              <div className="mt-1 flex items-baseline space-x-2">
                <span className="text-3xl font-extrabold text-slate-900 tracking-tight">
                  {gorakhpurData.rainfall7dMm}
                </span>
                <span className="text-sm font-semibold text-slate-500">mm</span>
              </div>
              <div className="mt-2 flex items-center text-xs font-bold text-emerald-600">
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
              <div className="w-11 h-11 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center">
                <Waves className="w-6 h-6" />
              </div>
              <button
                className="w-7 h-7 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center group-hover:bg-blue-600 group-hover:text-white transition-all"
                aria-label="View Gorakhpur 7-Day Rainfall"
              >
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="mt-4">
              <p className="text-xs text-slate-500 font-medium">7-Day Rainfall</p>
              <p className="text-xs font-semibold text-blue-700">Gorakhpur</p>
              <div className="mt-1 flex items-baseline space-x-2">
                <span className="text-3xl font-extrabold text-slate-900 tracking-tight">
                  {gorakhpurData.rainfall30dMm}
                </span>
                <span className="text-sm font-semibold text-slate-500">mm</span>
              </div>
              <div className="mt-2 flex items-center text-xs font-bold text-emerald-600">
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
              <div className="w-11 h-11 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center">
                <Sun className="w-6 h-6" />
              </div>
              <button
                className="w-7 h-7 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center group-hover:bg-amber-600 group-hover:text-white transition-all"
                aria-label="View Mahoba 90-Day Rainfall"
              >
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="mt-4">
              <p className="text-xs text-slate-500 font-medium">90-Day Rainfall</p>
              <p className="text-xs font-semibold text-amber-700">Mahoba</p>
              <div className="mt-1 flex items-baseline space-x-2">
                <span className="text-3xl font-extrabold text-slate-900 tracking-tight">
                  {mahobaData.rainfall90dMm}
                </span>
                <span className="text-sm font-semibold text-slate-500">mm</span>
              </div>
              <div className="mt-2 flex items-center text-xs font-bold text-rose-600">
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
              <div className="w-11 h-11 rounded-xl bg-orange-100 text-orange-700 flex items-center justify-center">
                <Sprout className="w-6 h-6" />
              </div>
              <button
                className="w-7 h-7 rounded-full bg-orange-100 text-orange-700 flex items-center justify-center group-hover:bg-orange-600 group-hover:text-white transition-all"
                aria-label="View Mahoba Seasonal Deficit"
              >
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="mt-4">
              <p className="text-xs text-slate-500 font-medium">Seasonal Deficit</p>
              <p className="text-xs font-semibold text-orange-700">Mahoba</p>
              <div className="mt-1 flex items-baseline space-x-2">
                <span className="text-3xl font-extrabold text-rose-600 tracking-tight">
                  {mahobaData.seasonalDeficitPct}%
                </span>
              </div>
              <div className="mt-2 flex items-center text-xs font-semibold text-amber-800">
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
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
                  <MapPin className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Risk Map Overview</h3>
                  <p className="text-[11px] text-slate-500">Uttar Pradesh pilot zones</p>
                </div>
              </div>

              <select
                value={selectedLocation}
                onChange={(e) => setSelectedLocation(e.target.value as any)}
                className="bg-slate-50 border border-slate-200 text-xs text-slate-800 rounded-lg px-2.5 py-1 focus:outline-none focus:border-blue-500"
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
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div className="flex items-center space-x-2">
                  <Calendar className="w-4 h-4 text-blue-600" />
                  <h3 className="text-sm font-bold text-slate-900">Recent Rainfall Trend</h3>
                </div>
                <select
                  value={trendDistrict}
                  onChange={(e) => setTrendDistrict(e.target.value as any)}
                  className="bg-slate-50 border border-slate-200 text-xs text-slate-800 rounded-lg px-2 py-1 focus:outline-none focus:border-blue-500"
                >
                  <option value="gorakhpur">Gorakhpur</option>
                  <option value="mahoba">Mahoba</option>
                </select>
              </div>

              {/* Range Selector Pills */}
              <div className="flex items-center gap-1.5 mt-3 p-1 rounded-xl bg-slate-100 border border-slate-200 text-xs">
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
                        ? 'bg-white text-blue-700 shadow-sm border border-slate-200 font-semibold'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {range.label}
                  </button>
                ))}
              </div>

              {/* Chart Component */}
              <div className="mt-4">
                {!isConfiguredPilot ? (
                  <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200 text-center space-y-3">
                    <div className="w-10 h-10 mx-auto rounded-xl bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center">
                      <Database className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-900">
                        No Historical Telemetry Ingested for {activeLocationData.name}
                      </h4>
                      <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                        Daily precipitation series pending onboarding into partition table. JalRakshak integrity rules strictly prevent proxy interpolation from Gorakhpur or Mahoba.
                      </p>
                    </div>
                    <div className="flex items-center justify-center gap-2 pt-1">
                      <button
                        onClick={() => {
                          setSelectedLocation('gorakhpur');
                          setTrendDistrict('gorakhpur');
                        }}
                        className="px-2.5 py-1 rounded-lg bg-sky-50 text-sky-700 hover:bg-sky-100 border border-sky-200 text-[11px] font-semibold transition"
                      >
                        View Gorakhpur Series
                      </button>
                      <button
                        onClick={() => {
                          setSelectedLocation('mahoba');
                          setTrendDistrict('mahoba');
                        }}
                        className="px-2.5 py-1 rounded-lg bg-amber-50 text-amber-800 hover:bg-amber-100 border border-amber-200 text-[11px] font-semibold transition"
                      >
                        View Mahoba Series
                      </button>
                    </div>
                  </div>
                ) : (
                  <RainfallChart
                    data={chartData}
                    barColor={trendDistrict === 'gorakhpur' ? '#0284c7' : '#d97706'}
                    lineColor="#2563eb"
                    height={190}
                  />
                )}
              </div>
            </div>

            {/* Key Insights bullets */}
            <div className="mt-4 pt-3 border-t border-slate-100 space-y-2">
              <div className="text-xs font-bold text-slate-700 flex items-center space-x-1.5">
                <Info className="w-3.5 h-3.5 text-blue-600" />
                <span>Key Insights</span>
              </div>
              <ul className="text-xs text-slate-600 space-y-1.5">
                <li className="flex items-start space-x-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-600 mt-1.5 shrink-0" />
                  <span>
                    {!isConfiguredPilot
                      ? `Observational pipeline for ${activeLocationData.name} (${activeLocationData.region}) is awaiting ingestion.`
                      : trendDistrict === 'gorakhpur'
                      ? 'Recent rainfall is significantly higher than historical average for this period.'
                      : 'Accumulated precipitation is 58% below 10-year seasonal median.'}
                  </span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 mt-1.5 shrink-0" />
                  <span>
                    {!isConfiguredPilot
                      ? 'Zero data bleed: candidate districts do not inherit telemetry or hazard models from pilot zones.'
                      : trendDistrict === 'gorakhpur'
                      ? 'Low-lying areas near Rapti river may be more vulnerable.'
                      : 'Soil moisture depletion indicates emerging agricultural stress in Bundelkhand.'}
                  </span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-600 mt-1.5 shrink-0" />
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
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <h3 className="text-xs font-bold text-slate-900 flex items-center space-x-1.5">
                <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
                <span>Alert & Updates</span>
              </h3>
              <button
                onClick={() => setCurrentRoute('monitoring')}
                className="text-[11px] text-blue-600 hover:text-blue-800 font-semibold hover:underline flex items-center"
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
                className="p-2.5 rounded-xl bg-rose-50 border border-rose-200 hover:border-rose-300 cursor-pointer transition shadow-sm"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-rose-900">High Rainfall Alert</span>
                  <span className="text-[10px] text-rose-700 bg-rose-100 px-1 rounded font-mono font-semibold">Gorakhpur</span>
                </div>
                <p className="text-[11px] text-slate-600 mt-0.5 leading-snug">
                  Recent rainfall significantly above historical average.
                </p>
              </div>

              <div
                onClick={() => {
                  setSelectedLocation('mahoba');
                  setCurrentRoute('drought');
                }}
                className="p-2.5 rounded-xl bg-amber-50 border border-amber-200 hover:border-amber-300 cursor-pointer transition shadow-sm"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-amber-900">Drought Watch</span>
                  <span className="text-[10px] text-amber-800 bg-amber-100 px-1 rounded font-mono font-semibold">Mahoba</span>
                </div>
                <p className="text-[11px] text-slate-600 mt-0.5 leading-snug">
                  Rainfall below historical average for the season.
                </p>
              </div>
            </div>
          </Card>

          {/* Card 2: Key Locations */}
          <Card className="p-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <h3 className="text-xs font-bold text-slate-900 flex items-center space-x-1.5">
                <MapPin className="w-3.5 h-3.5 text-blue-600" />
                <span>Key Locations</span>
              </h3>
              <button
                onClick={() => setCurrentRoute('map')}
                className="text-[11px] text-blue-600 hover:text-blue-800 font-semibold hover:underline flex items-center"
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
                className="p-2 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 flex items-center justify-between cursor-pointer transition"
              >
                <div className="flex items-center space-x-2.5">
                  <div className="w-7 h-7 rounded-lg bg-sky-100 text-sky-700 flex items-center justify-center">
                    <MapPin className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-900">Gorakhpur</div>
                    <div className="text-[10px] text-slate-500 font-mono">26.7606° N, 83.3732° E</div>
                  </div>
                </div>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-sky-100 text-sky-700 border border-sky-200">
                  Flood Focus
                </span>
              </div>

              <div
                onClick={() => {
                  setSelectedLocation('mahoba');
                  setCurrentRoute('drought');
                }}
                className="p-2 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 flex items-center justify-between cursor-pointer transition"
              >
                <div className="flex items-center space-x-2.5">
                  <div className="w-7 h-7 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center">
                    <MapPin className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-900">Mahoba</div>
                    <div className="text-[10px] text-slate-500 font-mono">25.2953° N, 79.8630° E</div>
                  </div>
                </div>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200">
                  Drought Focus
                </span>
              </div>
            </div>
          </Card>

          {/* Card 3: Data Sources */}
          <Card className="p-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <h3 className="text-xs font-bold text-slate-900 flex items-center space-x-1.5">
                <Database className="w-3.5 h-3.5 text-blue-600" />
                <span>Data Sources</span>
              </h3>
              <button
                onClick={() => setCurrentRoute('sources')}
                className="text-[11px] text-blue-600 hover:text-blue-800 font-semibold hover:underline flex items-center"
              >
                View All <ChevronRight className="w-3 h-3" />
              </button>
            </div>
            <div className="mt-3 space-y-1.5 text-xs text-slate-600">
              <div className="flex items-center justify-between p-1.5 rounded-lg bg-slate-50 border border-slate-100">
                <span className="font-semibold text-slate-900">NASA GPM IMERG</span>
                <span className="text-[10px] text-slate-500 font-mono">0.1° Gridded Sat</span>
              </div>
              <div className="flex items-center justify-between p-1.5 rounded-lg bg-slate-50 border border-slate-100">
                <span className="font-semibold text-slate-900">CHIRPS Daily</span>
                <span className="text-[10px] text-slate-500 font-mono">1981–Present</span>
              </div>
              <div className="flex items-center justify-between p-1.5 rounded-lg bg-slate-50 border border-slate-100">
                <span className="font-semibold text-slate-900">SRTM DEM</span>
                <span className="text-[10px] text-slate-500 font-mono">30m Elevation</span>
              </div>
              <div className="flex items-center justify-between p-1.5 rounded-lg bg-slate-50 border border-slate-100">
                <span className="font-semibold text-slate-900">UPSDMA / IMD</span>
                <span className="text-[10px] text-emerald-700 font-semibold">Official Warning Links</span>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* 4. Bottom Row Action Shortcuts (4 cards matching the approved mockup) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-2">
        <button
          onClick={() => setCurrentRoute('trends')}
          className="flex items-center justify-between p-4 rounded-2xl bg-white border border-slate-200 hover:border-blue-400 hover:shadow-md transition-all interactive-btn text-left group shadow-sm"
        >
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
              <BarChart2 className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
                Rainfall & Trends
              </div>
              <div className="text-xs text-slate-500">Historical analysis</div>
            </div>
          </div>
          <ChevronRight className="w-5 h-5 text-slate-400 group-hover:text-blue-600 group-hover:translate-x-1 transition-all" />
        </button>

        <button
          onClick={() => setCurrentRoute('assistant')}
          className="flex items-center justify-between p-4 rounded-2xl bg-white border border-slate-200 hover:border-blue-400 hover:shadow-md transition-all interactive-btn text-left group shadow-sm"
        >
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-sky-50 text-sky-600 flex items-center justify-center">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-bold text-slate-900 group-hover:text-sky-600 transition-colors">
                AI Assistant
              </div>
              <div className="text-xs text-slate-500">Ask questions</div>
            </div>
          </div>
          <ChevronRight className="w-5 h-5 text-slate-400 group-hover:text-sky-600 group-hover:translate-x-1 transition-all" />
        </button>

        <button
          onClick={() => setCurrentRoute('preparedness')}
          className="flex items-center justify-between p-4 rounded-2xl bg-white border border-slate-200 hover:border-emerald-400 hover:shadow-md transition-all interactive-btn text-left group shadow-sm"
        >
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-bold text-slate-900 group-hover:text-emerald-600 transition-colors">
                Preparedness
              </div>
              <div className="text-xs text-slate-500">Safety guidelines</div>
            </div>
          </div>
          <ChevronRight className="w-5 h-5 text-slate-400 group-hover:text-emerald-600 group-hover:translate-x-1 transition-all" />
        </button>

        <button
          onClick={() => setCurrentRoute('sources')}
          className="flex items-center justify-between p-4 rounded-2xl bg-white border border-slate-200 hover:border-amber-400 hover:shadow-md transition-all interactive-btn text-left group shadow-sm"
        >
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-700 flex items-center justify-center">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-bold text-slate-900 group-hover:text-amber-700 transition-colors">
                Data Sources
              </div>
              <div className="text-xs text-slate-500">Transparent data</div>
            </div>
          </div>
          <ChevronRight className="w-5 h-5 text-slate-400 group-hover:text-amber-600 group-hover:translate-x-1 transition-all" />
        </button>
      </div>
    </div>
  );
};
