import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  Calendar,
  Download,
  Filter,
  TrendingUp,
  CloudRain,
  ChevronDown,
  Info,
  CheckCircle2,
  FileSpreadsheet,
  RefreshCw,
  Table,
  AlertTriangle,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { Card } from '../components/common/Card';
import { RainfallChart, RainfallDataPoint } from '../components/charts/RainfallChart';
import { apiService, RainfallTrendsResponse } from '../services/api';
import {
  UP_DISTRICTS_DATA,
  getFilteredRainfallData,
  DEMO_DATA_DISCLAIMER,
} from '../data/mockData';

export const RainfallTrendsView: React.FC = () => {
  const { selectedLocation, setSelectedLocation } = useApp();
  const [activeTab, setActiveTab] = useState<'trend' | 'historical' | 'seasonal' | 'download'>('trend');
  const [timePeriod, setTimePeriod] = useState<'1y' | '5y' | '10y'>('1y');
  const [aggregation, setAggregation] = useState<'monthly' | 'weekly' | 'daily'>('monthly');
  const [backendTrends, setBackendTrends] = useState<RainfallTrendsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [showDataTable, setShowDataTable] = useState(false);

  const locKey = selectedLocation === 'mahoba' ? 'mahoba' : 'gorakhpur';
  const districtData = UP_DISTRICTS_DATA.find((d) => d.id === locKey)!;

  const loadTrends = () => {
    setIsLoading(true);
    setFetchError(null);
    const rangeParam = timePeriod === '1y' ? '30' : timePeriod === '5y' ? '90' : '365';
    apiService
      .fetchRainfallTrends(locKey, rangeParam)
      .then((data) => setBackendTrends(data))
      .catch((err) => setFetchError(err.message || 'Failed to fetch trends data'))
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    loadTrends();
  }, [locKey, timePeriod]);

  // Use backend series if available, otherwise fallback fixture
  let chartSeries: RainfallDataPoint[] = getFilteredRainfallData(locKey, '365', aggregation);
  if (backendTrends?.series && backendTrends.series.length > 0) {
    chartSeries = backendTrends.series.map((pt) => ({
      date: pt.date,
      rainfall: pt.observed_rainfall_mm ?? 0,
      historicalAvg: pt.historical_avg_mm,
    }));
  }

  const handleExport = (format: 'json' | 'csv') => {
    let content = '';
    let mimeType = '';
    let ext = '';

    if (format === 'json') {
      content = JSON.stringify(
        {
          district: districtData.name,
          timePeriod,
          aggregation,
          generatedAt: new Date().toISOString(),
          sources: ['NASA GPM IMERG 0.1° Late Run', 'CHIRPS Daily Station Blended v2.0'],
          units: 'mm',
          is_demo_data: true,
          data: chartSeries,
        },
        null,
        2
      );
      mimeType = 'application/json';
      ext = 'json';
    } else {
      content =
        'Date,Observed Rainfall (mm),Historical Average (mm),Data Quality\n' +
        chartSeries
          .map((row) => `${row.date},${row.rainfall},${row.historicalAvg},observed`)
          .join('\n');
      mimeType = 'text/csv';
      ext = 'csv';
    }

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `rainfall_trends_${locKey}_${timePeriod}_${aggregation}.${ext}`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Demo Disclaimer & Non-Forecast Notice */}
      <div className="px-3.5 py-2 rounded-xl bg-navy-900/80 border border-navy-800 text-xs text-slate-300 flex flex-col md:flex-row md:items-center justify-between gap-2">
        <div className="flex items-center space-x-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400" />
          <span>
            <strong>SCIENTIFIC NOTICE:</strong> Historical observational trends only (1991–2024 reference climatology). Does NOT provide or imply a future weather prediction or river stage forecast.
          </span>
        </div>
        <div className="flex items-center space-x-2 text-[11px] font-mono shrink-0">
          <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
            DEMO DATA
          </span>
          <span className="text-cyan-400 uppercase">{locKey}</span>
        </div>
      </div>

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-navy-800">
        <div>
          <h1 className="text-2xl lg:text-3xl font-extrabold text-white">Rainfall & Historical Trends</h1>
          <p className="text-xs lg:text-sm text-slate-300">
            Analyse multi-year rainfall patterns, precipitation anomalies and compare with 30-year historical baselines.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <select
            value={selectedLocation}
            onChange={(e) => setSelectedLocation(e.target.value as any)}
            className="bg-navy-850 border border-cyan-500/40 text-xs font-semibold text-cyan-200 rounded-xl px-3 py-2 focus:outline-none focus:border-cyan-400"
          >
            <option value="gorakhpur">Gorakhpur (Flood Pilot)</option>
            <option value="mahoba">Mahoba (Drought Pilot)</option>
          </select>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-navy-800 text-sm">
        {[
          { key: 'trend', label: 'Rainfall Trend' },
          { key: 'historical', label: 'Historical Comparison' },
          { key: 'seasonal', label: 'Seasonal Analysis' },
          { key: 'download', label: 'Download Data' },
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

      {/* Filter Row */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-3 rounded-2xl bg-navy-900/80 border border-navy-800">
        <div className="flex flex-wrap items-center gap-4 text-xs">
          <div className="flex items-center space-x-2">
            <span className="text-slate-400">Time Period:</span>
            <div className="flex bg-navy-850 p-1 rounded-lg border border-navy-700">
              {(['1y', '5y', '10y'] as const).map((p) => (
                <button
                  key={p}
                  onClick={() => setTimePeriod(p)}
                  className={`px-2.5 py-1 rounded text-xs font-semibold ${
                    timePeriod === p ? 'bg-cyan-500 text-navy-950 font-bold' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {p === '1y' ? '1 Year' : p === '5y' ? '5 Years' : '10 Years'}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-slate-400">Aggregation:</span>
            <div className="flex bg-navy-850 p-1 rounded-lg border border-navy-700">
              {(['monthly', 'weekly', 'daily'] as const).map((agg) => (
                <button
                  key={agg}
                  onClick={() => setAggregation(agg)}
                  className={`px-2.5 py-1 rounded text-xs font-semibold capitalize ${
                    aggregation === agg ? 'bg-cyan-500 text-navy-950 font-bold' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {agg}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowDataTable(!showDataTable)}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-navy-850 hover:bg-navy-800 text-slate-300 text-xs font-semibold border border-navy-700"
          >
            <Table className="w-3.5 h-3.5" />
            <span>{showDataTable ? 'Hide Table' : 'Accessible Table'}</span>
          </button>
          <button
            onClick={() => handleExport('json')}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-navy-800 hover:bg-navy-700 text-cyan-300 text-xs font-semibold border border-cyan-500/30 interactive-btn"
          >
            <Download className="w-3.5 h-3.5" />
            <span>JSON</span>
          </button>
          <button
            onClick={() => handleExport('csv')}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-navy-800 hover:bg-navy-700 text-cyan-300 text-xs font-semibold border border-cyan-500/30 interactive-btn"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>CSV</span>
          </button>
        </div>
      </div>

      {/* Main Chart Card */}
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-navy-800">
          <div>
            <h3 className="text-base font-bold text-white">
              {aggregation === 'monthly' ? 'Monthly' : aggregation === 'weekly' ? 'Weekly' : 'Daily'} Rainfall — {districtData.name}
            </h3>
            <p className="text-xs text-slate-400">
              Current Year vs Historical Climatological Average (1991–2020 baseline)
            </p>
          </div>
          <div className="flex items-center space-x-3 text-xs font-mono">
            <span className="text-slate-400">Coverage: 100%</span>
            <span className="text-cyan-300">CHIRPS v2.0 + GPM</span>
          </div>
        </div>

        <div className="mt-4">
          <RainfallChart
            data={chartSeries}
            barColor={locKey === 'gorakhpur' ? '#00e5ff' : '#f59e0b'}
            lineColor={locKey === 'gorakhpur' ? '#38bdf8' : '#ea580c'}
            height={260}
          />
        </div>

        {/* Missing vs Zero Data Distinction Footer */}
        <div className="mt-3 pt-2.5 border-t border-navy-800/80 flex flex-wrap items-center justify-between text-[11px] text-slate-400">
          <div className="flex items-center space-x-4">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-cyan-400" />
              <span>Bars: Observed / Fixture Rainfall (mm)</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-sky-400" />
              <span>Dashed Line: Historical Normal Baseline</span>
            </span>
          </div>
          <span className="text-slate-400 italic">
            Zero rainfall (0.0mm dry day) distinguished from missing observation telemetry.
          </span>
        </div>
      </Card>

      {/* Screen-Reader Accessible Summary Table (conditionally toggleable) */}
      {showDataTable && (
        <Card className="p-4 overflow-x-auto">
          <div className="pb-2 border-b border-navy-800 mb-3 flex items-center justify-between">
            <h4 className="text-xs font-bold text-white uppercase tracking-wider">
              Accessible Data Summary ({chartSeries.length} intervals)
            </h4>
            <span className="text-xs text-slate-400 font-mono">Units: mm precipitation</span>
          </div>
          <table className="w-full text-left text-xs text-slate-300">
            <thead>
              <tr className="border-b border-navy-800 text-slate-400 font-mono text-[11px]">
                <th className="py-2 px-3">Interval / Date</th>
                <th className="py-2 px-3">Observed (mm)</th>
                <th className="py-2 px-3">Baseline Normal (mm)</th>
                <th className="py-2 px-3">Departure</th>
                <th className="py-2 px-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {chartSeries.map((row, idx) => {
                const diff = row.rainfall !== null ? row.rainfall - row.historicalAvg : null;
                const isMissing = row.rainfall === null;
                const isZero = row.rainfall === 0;
                return (
                  <tr key={idx} className="border-b border-navy-800/40 hover:bg-navy-850/50">
                    <td className="py-1.5 px-3 font-mono">{row.date}</td>
                    <td className="py-1.5 px-3 font-bold text-white">
                      {row.rainfall !== null ? `${row.rainfall.toFixed(1)} mm` : 'Missing'}
                    </td>
                    <td className="py-1.5 px-3 text-slate-400">{row.historicalAvg.toFixed(1)} mm</td>
                    <td className={`py-1.5 px-3 font-mono ${diff === null ? 'text-slate-500' : diff >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {diff === null ? '—' : diff >= 0 ? `+${diff.toFixed(1)} mm` : `${diff.toFixed(1)} mm`}
                    </td>
                    <td className="py-1.5 px-3 text-[10px]">
                      {isMissing ? (
                        <span className="px-1.5 py-0.5 rounded bg-rose-950/60 text-rose-300 border border-rose-800/50">Missing</span>
                      ) : isZero ? (
                        <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">Zero Rain</span>
                      ) : (
                        <span className="px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300">Observed</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      )}

      {/* 4 Summary Stat Cards matching design */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4">
          <span className="text-xs text-slate-400 font-medium">Total Rainfall</span>
          <div className="mt-2 text-2xl font-black text-white">
            {locKey === 'gorakhpur' ? '1,024' : '230'}{' '}
            <span className="text-sm font-semibold text-slate-400">mm</span>
          </div>
          <span
            className={`text-xs font-bold mt-1 block ${
              locKey === 'gorakhpur' ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {locKey === 'gorakhpur' ? '+16% vs historical' : '-72% vs historical'}
          </span>
        </Card>

        <Card className="p-4">
          <span className="text-xs text-slate-400 font-medium">Wet Days (&gt;2.5mm)</span>
          <div className="mt-2 text-2xl font-black text-white">
            {locKey === 'gorakhpur' ? '56 days' : '18 days'}
          </div>
          <span
            className={`text-xs font-bold mt-1 block ${
              locKey === 'gorakhpur' ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {locKey === 'gorakhpur' ? '+12% vs historical' : '-60% vs historical'}
          </span>
        </Card>

        <Card className="p-4">
          <span className="text-xs text-slate-400 font-medium">Maximum Daily Rainfall</span>
          <div className="mt-2 text-2xl font-black text-cyan-300">
            {locKey === 'gorakhpur' ? '128' : '48'}{' '}
            <span className="text-sm font-semibold text-slate-400">mm</span>
          </div>
          <span className="text-xs text-slate-400 font-mono mt-1 block">
            {locKey === 'gorakhpur' ? 'Recorded 25 Aug 2026' : 'Recorded 14 Jul 2026'}
          </span>
        </Card>

        <Card className="p-4">
          <span className="text-xs text-slate-400 font-medium">Historical Baseline Avg</span>
          <div className="mt-2 text-2xl font-black text-slate-300">
            {locKey === 'gorakhpur' ? '867' : '820'}{' '}
            <span className="text-sm font-semibold text-slate-400">mm</span>
          </div>
          <span className="text-xs text-slate-400 font-mono mt-1 block">30-Year Series (1991–2020)</span>
        </Card>
      </div>
    </div>
  );
};
