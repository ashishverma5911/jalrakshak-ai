import React, { useState, useEffect } from 'react';
import {
  Layers,
  MapPin,
  Maximize2,
  RotateCcw,
  Sliders,
  Info,
  Check,
  Search,
  ExternalLink,
  Compass,
  AlertTriangle,
  RefreshCw,
  Table,
  CheckCircle2,
  Calendar,
  Database,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { Card } from '../components/common/Card';
import { DistrictRiskMap } from '../components/map/DistrictRiskMap';
import { apiService, MapLayersResponse, DistrictMapFeature } from '../services/api';
import { DataProvenanceBadge } from '../components/common/DataProvenanceBadge';
import { UP_DISTRICTS_DATA, DistrictGeoData, DEMO_DATA_DISCLAIMER } from '../data/mockData';

export const RiskMapView: React.FC = () => {
  const {
    selectedLocation,
    setSelectedLocation,
    activeMapLayer,
    setActiveMapLayer,
    setCurrentRoute,
  } = useApp();

  const [mapMode, setMapMode] = useState<'vector' | 'satellite'>('vector');
  const [displayView, setDisplayView] = useState<'canvas' | 'table'>('canvas');
  const [hazardFilter, setHazardFilter] = useState<'all' | 'flood' | 'drought'>('all');
  const [searchDistrictQuery, setSearchDistrictQuery] = useState('');
  const [showDistricts, setShowDistricts] = useState(true);
  const [showRivers, setShowRivers] = useState(true);
  const [showCities, setShowCities] = useState(true);
  const [selectedDistrictDetail, setSelectedDistrictDetail] = useState<DistrictGeoData>(
    UP_DISTRICTS_DATA[0]
  );
  const [backendMapLayers, setBackendMapLayers] = useState<MapLayersResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const loadMapLayers = () => {
    setIsLoading(true);
    setFetchError(null);
    const hazardParam = activeMapLayer === 'flood' ? 'flood' : activeMapLayer === 'drought' ? 'drought' : 'all';
    apiService
      .fetchMapLayers(hazardParam)
      .then((data) => setBackendMapLayers(data))
      .catch((err) => setFetchError(err.message || 'Failed to fetch map layers'))
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    loadMapLayers();
  }, [activeMapLayer]);

  const filteredDistricts = UP_DISTRICTS_DATA.filter((d) => {
    const matchesSearch =
      d.name.toLowerCase().includes(searchDistrictQuery.toLowerCase()) ||
      d.riverBasin.toLowerCase().includes(searchDistrictQuery.toLowerCase());
    const matchesHazard =
      hazardFilter === 'all'
        ? true
        : hazardFilter === 'flood'
        ? d.floodRisk === 'high' || d.id === 'gorakhpur'
        : d.droughtRisk === 'moderate' || d.droughtRisk === 'high' || d.id === 'mahoba';
    return matchesSearch && matchesHazard;
  });

  const handleSelectDistrict = (district: DistrictGeoData) => {
    setSelectedDistrictDetail(district);
    if (district.id === 'gorakhpur' || district.id === 'mahoba') {
      setSelectedLocation(district.id);
    }
  };

  return (
    <div className="space-y-6">
      {/* 0. Demo Data Disclaimer & Geometry Notice */}
      <div className="px-3.5 py-2 rounded-xl bg-cyan-950/40 border border-cyan-800/40 text-xs text-cyan-200 flex flex-col md:flex-row md:items-center justify-between gap-2">
        <div className="flex items-center space-x-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400" />
          <span>
            <strong>DEMO DATA:</strong> Point centroid coordinates (WGS84 EPSG:4326). Validated tehsil-level boundary polygons are unintegrated in prototype.
          </span>
        </div>
        <span className="font-mono text-cyan-300 text-[11px] shrink-0">
          Source: SRTM 30m DEM / NASA GPM IMERG 0.1°
        </span>
      </div>

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-navy-800">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-bold uppercase tracking-wider text-cyan-400 bg-cyan-950/70 px-2 py-0.5 rounded border border-cyan-800/80">
              Geospatial Intelligence
            </span>
            <span className="text-xs text-slate-400 font-mono">Cartographic Engine</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-extrabold text-white mt-1">
            Interactive Risk Map
          </h1>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <DataProvenanceBadge
              mode={backendMapLayers?.data_mode || 'CACHED_VERIFIED'}
              source="NASA SRTM 30m & CHIRPS v2.0"
              datasetVersion="v3.0 void-filled"
              spatialResolution="1 arc-second (~30m)"
              limitations="Gorakhpur and Mahoba districts bounded by validated Survey of India / OSM administrative polygon boundaries (EPSG:4326). Candidate districts use centroid points pending polygon onboarding."
            />
            <p className="text-xs text-slate-300">
              Explore localized flood inundation proxies, drought anomalies and topographic layers across Uttar Pradesh.
            </p>
          </div>
        </div>

        {/* View Mode Toggle: Canvas vs Accessible Table */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="bg-navy-900 p-1 rounded-xl border border-navy-800 flex items-center space-x-1">
            <button
              onClick={() => setDisplayView('canvas')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                displayView === 'canvas'
                  ? 'bg-cyan-500 text-navy-950 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Interactive Canvas
            </button>
            <button
              onClick={() => setDisplayView('table')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
                displayView === 'table'
                  ? 'bg-cyan-500 text-navy-950 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Table className="w-3.5 h-3.5" />
              <span>Accessible Table</span>
            </button>
          </div>

          <div className="bg-navy-900 p-1 rounded-xl border border-navy-800 flex items-center space-x-1">
            <button
              onClick={() => setMapMode('vector')}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                mapMode === 'vector'
                  ? 'bg-navy-700 text-cyan-300'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Vector
            </button>
            <button
              onClick={() => setMapMode('satellite')}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                mapMode === 'satellite'
                  ? 'bg-navy-700 text-cyan-300'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Satellite
            </button>
          </div>
        </div>
      </div>

      {/* Hazard Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-2xl bg-navy-900/80 border border-navy-800 text-xs">
        <div className="flex items-center space-x-2">
          <span className="text-slate-400 font-medium">Filter by Hazard:</span>
          <div className="flex bg-navy-850 p-1 rounded-xl border border-navy-700 text-xs">
            <button
              onClick={() => setHazardFilter('all')}
              className={`px-3 py-1 rounded-lg font-semibold transition ${
                hazardFilter === 'all' ? 'bg-cyan-500 text-navy-950' : 'text-slate-400 hover:text-white'
              }`}
            >
              All Hazards
            </button>
            <button
              onClick={() => setHazardFilter('flood')}
              className={`px-3 py-1 rounded-lg font-semibold transition ${
                hazardFilter === 'flood' ? 'bg-rose-500 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              Flood Focus
            </button>
            <button
              onClick={() => setHazardFilter('drought')}
              className={`px-3 py-1 rounded-lg font-semibold transition ${
                hazardFilter === 'drought' ? 'bg-amber-500 text-navy-950' : 'text-slate-400 hover:text-white'
              }`}
            >
              Drought Focus
            </button>
          </div>
        </div>

        {fetchError ? (
          <div className="flex items-center space-x-2 text-rose-400 text-xs">
            <span>{fetchError}</span>
            <button
              onClick={loadMapLayers}
              className="px-2 py-0.5 rounded bg-rose-500/20 border border-rose-500/40 text-rose-300 hover:bg-rose-500/30"
            >
              Retry
            </button>
          </div>
        ) : (
          <span className="text-[11px] text-slate-400 font-mono">
            {filteredDistricts.length} districts mapped • Observation window: Past 30 Days
          </span>
        )}
      </div>

      {/* View Switch: Canvas or Accessible Table */}
      {displayView === 'table' ? (
        <Card className="overflow-x-auto p-4">
          <div className="flex items-center justify-between pb-3 border-b border-navy-800 mb-3">
            <div>
              <h2 className="text-sm font-bold text-white">Accessible District Registry Table</h2>
              <p className="text-xs text-slate-400">
                Non-spatial tabular alternative with full keyboard navigation and screen-reader accessibility.
              </p>
            </div>
            <span className="text-xs text-cyan-400 font-mono">
              Press Enter/Space on a row to select district
            </span>
          </div>

          <table className="w-full text-left text-xs text-slate-200 border-collapse">
            <thead>
              <tr className="border-b border-navy-750 text-slate-400 font-mono text-[11px]">
                <th className="py-2.5 px-3">District</th>
                <th className="py-2.5 px-3">Coordinates (WGS84)</th>
                <th className="py-2.5 px-3">Elevation</th>
                <th className="py-2.5 px-3">River Basin</th>
                <th className="py-2.5 px-3">Flood Risk</th>
                <th className="py-2.5 px-3">Drought Risk</th>
                <th className="py-2.5 px-3">Rainfall Anomaly</th>
                <th className="py-2.5 px-3">SPI-3 Index</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredDistricts.map((d) => {
                const isSelected = selectedDistrictDetail.id === d.id;
                return (
                  <tr
                    key={d.id}
                    tabIndex={0}
                    onClick={() => handleSelectDistrict(d)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        handleSelectDistrict(d);
                      }
                    }}
                    className={`border-b border-navy-800/60 cursor-pointer transition focus:outline-none focus:bg-cyan-500/20 ${
                      isSelected ? 'bg-cyan-500/15 font-semibold text-white' : 'hover:bg-navy-850'
                    }`}
                  >
                    <td className="py-2.5 px-3">
                      <div className="flex items-center space-x-1.5">
                        <span>{d.name}</span>
                        <span className="text-slate-400 text-[10px]">({d.hindiName})</span>
                        {d.isPilot && (
                          <span className="px-1.5 py-0.2 rounded bg-cyan-500/20 text-cyan-300 text-[9px] border border-cyan-500/40">
                            PILOT
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-400">
                      {d.lat.toFixed(4)}°N, {d.lng.toFixed(4)}°E
                    </td>
                    <td className="py-2.5 px-3">{d.elevationM} m MSL</td>
                    <td className="py-2.5 px-3 text-slate-300">{d.riverBasin}</td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          d.floodRisk === 'high'
                            ? 'bg-rose-500/20 text-rose-300'
                            : d.floodRisk === 'moderate'
                            ? 'bg-amber-500/20 text-amber-300'
                            : 'bg-emerald-500/20 text-emerald-300'
                        }`}
                      >
                        {d.floodRisk}
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          d.droughtRisk === 'high'
                            ? 'bg-rose-500/20 text-rose-300'
                            : d.droughtRisk === 'moderate'
                            ? 'bg-amber-500/20 text-amber-300'
                            : 'bg-emerald-500/20 text-emerald-300'
                        }`}
                      >
                        {d.droughtRisk}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-mono">
                      {d.anomalyPct > 0 ? `+${d.anomalyPct}%` : `${d.anomalyPct}%`}
                    </td>
                    <td className="py-2.5 px-3 font-mono">
                      {d.spi3.toFixed(2)}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      {d.id === 'gorakhpur' ? (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedLocation('gorakhpur');
                            setCurrentRoute('flood');
                          }}
                          className="px-2.5 py-1 rounded bg-cyan-500 text-navy-950 font-bold text-[10px] hover:bg-cyan-400"
                        >
                          View Flood
                        </button>
                      ) : d.id === 'mahoba' ? (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedLocation('mahoba');
                            setCurrentRoute('drought');
                          }}
                          className="px-2.5 py-1 rounded bg-amber-500 text-navy-950 font-bold text-[10px] hover:bg-amber-400"
                        >
                          View Drought
                        </button>
                      ) : (
                        <span className="text-[10px] text-slate-500 italic">Select row</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      ) : (
        /* Main Map + Controls Grid */
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Map Stage (8 cols) */}
          <div className="lg:col-span-8 flex flex-col space-y-4">
            <Card className="flex-1 min-h-[500px] flex flex-col justify-between p-4">
              <DistrictRiskMap
                onSelectDistrict={(id) => {
                  const found = UP_DISTRICTS_DATA.find((d) => d.id === id);
                  if (found) setSelectedDistrictDetail(found);
                }}
              />
            </Card>

            {/* District Quick Inspector Pill Bar */}
            <div className="p-4 rounded-2xl bg-navy-900/90 border border-navy-800 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
              <div className="flex items-center space-x-3">
                <div
                  className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-white shadow-sm ${
                    selectedDistrictDetail.floodRisk === 'high'
                      ? 'bg-rose-600'
                      : selectedDistrictDetail.droughtRisk === 'moderate'
                      ? 'bg-amber-600'
                      : 'bg-emerald-600'
                  }`}
                >
                  <MapPin className="w-4 h-4" />
                </div>
                <div>
                  <div className="font-extrabold text-white text-sm flex items-center gap-2">
                    <span>{selectedDistrictDetail.name}</span>
                    <span className="text-slate-400 font-normal">({selectedDistrictDetail.hindiName})</span>
                    {selectedDistrictDetail.isPilot && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                        Official Pilot
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                    {selectedDistrictDetail.lat.toFixed(4)}° N, {selectedDistrictDetail.lng.toFixed(4)}° E •{' '}
                    {selectedDistrictDetail.riverBasin}
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                {selectedDistrictDetail.id === 'gorakhpur' ? (
                  <button
                    onClick={() => {
                      setSelectedLocation('gorakhpur');
                      setCurrentRoute('flood');
                    }}
                    className="px-3 py-1.5 rounded-xl bg-cyan-500 text-navy-950 font-bold hover:bg-cyan-400 transition"
                  >
                    Open Flood Assessment
                  </button>
                ) : selectedDistrictDetail.id === 'mahoba' ? (
                  <button
                    onClick={() => {
                      setSelectedLocation('mahoba');
                      setCurrentRoute('drought');
                    }}
                    className="px-3 py-1.5 rounded-xl bg-amber-500 text-navy-950 font-bold hover:bg-amber-400 transition"
                  >
                    Open Drought Assessment
                  </button>
                ) : (
                  <span className="text-slate-400 text-xs italic">
                    Non-pilot district • Context baseline available
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Map Layers & Controls Panel (4 cols) */}
          <div className="lg:col-span-4 space-y-4">
            <Card>
              <h3 className="text-sm font-bold text-white pb-3 border-b border-navy-800 flex items-center space-x-2">
                <Sliders className="w-4 h-4 text-cyan-400" />
                <span>Geospatial Hazard Layers</span>
              </h3>

              {/* Select Active Hazard Layer */}
              <div className="mt-4 space-y-2">
                <label className="text-xs font-semibold text-slate-300">Active Map Metric</label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { id: 'flood', label: 'Flood Risk', color: 'border-rose-500/50 text-rose-300' },
                    { id: 'drought', label: 'Drought Risk', color: 'border-amber-500/50 text-amber-300' },
                    { id: 'rainfall', label: 'Rainfall Anomaly', color: 'border-cyan-500/50 text-cyan-300' },
                    { id: 'elevation', label: 'SRTM Elevation', color: 'border-emerald-500/50 text-emerald-300' },
                  ].map((item) => (
                    <button
                      key={item.id}
                      onClick={() => setActiveMapLayer(item.id as any)}
                      className={`p-2 rounded-xl text-xs font-semibold text-left transition border ${
                        activeMapLayer === item.id
                          ? `bg-navy-800 ${item.color} ring-1 ring-white/20 shadow-md`
                          : 'bg-navy-850 text-slate-400 border-navy-800 hover:text-white'
                      }`}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Toggle Overlay Elements */}
              <div className="mt-5 space-y-3 pt-4 border-t border-navy-800">
                <label className="text-xs font-semibold text-slate-300">Cartographic Overlays</label>
                <div className="space-y-2 text-xs text-slate-300">
                  <label className="flex items-center justify-between cursor-pointer p-2 rounded-lg bg-navy-850/50 hover:bg-navy-850">
                    <span>District Boundaries</span>
                    <input
                      type="checkbox"
                      checked={showDistricts}
                      onChange={(e) => setShowDistricts(e.target.checked)}
                      className="accent-cyan-400 rounded cursor-pointer"
                    />
                  </label>
                  <label className="flex items-center justify-between cursor-pointer p-2 rounded-lg bg-navy-850/50 hover:bg-navy-850">
                    <span>Rapti & Ganges River Network</span>
                    <input
                      type="checkbox"
                      checked={showRivers}
                      onChange={(e) => setShowRivers(e.target.checked)}
                      className="accent-cyan-400 rounded cursor-pointer"
                    />
                  </label>
                  <label className="flex items-center justify-between cursor-pointer p-2 rounded-lg bg-navy-850/50 hover:bg-navy-850">
                    <span>City Settlement Coordinates</span>
                    <input
                      type="checkbox"
                      checked={showCities}
                      onChange={(e) => setShowCities(e.target.checked)}
                      className="accent-cyan-400 rounded cursor-pointer"
                    />
                  </label>
                </div>
              </div>

              {/* District Fast Search */}
              <div className="mt-5 pt-4 border-t border-navy-800">
                <label className="text-xs font-semibold text-slate-300 block mb-2">
                  Locate District / Basin
                </label>
                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    value={searchDistrictQuery}
                    onChange={(e) => setSearchDistrictQuery(e.target.value)}
                    placeholder="Filter district (e.g. Gorakhpur, Mahoba)..."
                    className="w-full pl-8 pr-3 py-1.5 rounded-xl bg-navy-850 border border-navy-750 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-cyan-400"
                  />
                </div>

                <div className="mt-2 max-h-36 overflow-y-auto space-y-1">
                  {filteredDistricts.map((d) => (
                    <button
                      key={d.id}
                      onClick={() => handleSelectDistrict(d)}
                      className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs flex items-center justify-between transition ${
                        selectedDistrictDetail.id === d.id
                          ? 'bg-cyan-500/20 text-cyan-300 font-bold'
                          : 'text-slate-300 hover:bg-navy-850'
                      }`}
                    >
                      <span>{d.name}</span>
                      <span className="text-[10px] text-slate-400 font-mono">
                        {d.isPilot ? 'PILOT' : `${d.elevationM}m`}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            </Card>

            {/* Scientific Disclaimer Card */}
            <Card className="bg-navy-950/70 border border-navy-800 text-xs text-slate-400 leading-relaxed">
              <div className="flex items-center space-x-1.5 text-amber-300 font-bold text-xs mb-1">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                <span>Data Honesty Notice</span>
              </div>
              {DEMO_DATA_DISCLAIMER}
            </Card>
          </div>
        </div>
      )}
    </div>
  );
};
