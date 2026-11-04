import React, { useState } from 'react';
import {
  ZoomIn,
  ZoomOut,
  Info,
  RotateCcw,
  ExternalLink,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { UP_DISTRICTS_DATA, DistrictGeoData } from '../../data/mockData';

interface DistrictRiskMapProps {
  compact?: boolean;
  onSelectDistrict?: (districtId: string) => void;
}

export const DistrictRiskMap: React.FC<DistrictRiskMapProps> = ({
  compact = false,
  onSelectDistrict,
}) => {
  const {
    setSelectedLocation,
    setCurrentRoute,
    activeMapLayer,
    setActiveMapLayer,
    selectedLocation,
    dataMode,
  } = useApp();

  const [zoomLevel, setZoomLevel] = useState(1);
  const [hoveredDistrict, setHoveredDistrict] = useState<DistrictGeoData | null>(null);

  const handleDistrictClick = (district: DistrictGeoData) => {
    if (onSelectDistrict) {
      onSelectDistrict(district.id);
    }

    if (district.id === 'gorakhpur') {
      setSelectedLocation('gorakhpur');
      setCurrentRoute('flood');
    } else if (district.id === 'mahoba') {
      setSelectedLocation('mahoba');
      setCurrentRoute('drought');
    }
  };

  // Convert real lat/lng to normalized SVG coordinates for UP bounding box:
  // UP bounding box approx: Lat 23.8° to 30.5°, Lng 77.0° to 84.8°
  const getCoordinates = (lat: number, lng: number) => {
    const minLng = 77.0;
    const maxLng = 84.8;
    const minLat = 23.8;
    const maxLat = 30.5;

    const x = ((lng - minLng) / (maxLng - minLng)) * 440 + 30;
    const y = ((maxLat - lat) / (maxLat - minLat)) * 260 + 25;
    return { x, y };
  };

  // Compute color based on active layer
  const getDistrictFill = (d: DistrictGeoData) => {
    if (activeMapLayer === 'flood') {
      if (d.floodRisk === 'high') return '#dc2626';
      if (d.floodRisk === 'moderate') return '#d97706';
      return '#0284c7';
    }
    if (activeMapLayer === 'drought') {
      if (d.droughtRisk === 'high') return '#dc2626';
      if (d.droughtRisk === 'moderate') return '#d97706';
      return '#16a34a';
    }
    if (activeMapLayer === 'rainfall') {
      return d.anomalyPct > 20 ? '#0284c7' : d.anomalyPct < -20 ? '#d97706' : '#0ea5e9';
    }
    // Elevation
    return d.elevationM > 200 ? '#78350f' : d.elevationM > 100 ? '#b45309' : '#0284c7';
  };

  return (
    <div className="relative w-full h-full min-h-[340px] flex flex-col justify-between overflow-hidden rounded-2xl bg-white border border-slate-200 p-4 shadow-sm select-none">
      {/* Top Map Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 z-10">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 rounded-full bg-blue-600 animate-pulse" />
          <span className="text-xs font-bold text-slate-900 tracking-wide">
            Uttar Pradesh Geospatial Risk Canvas
          </span>
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-mono hidden sm:inline">
            77°E–85°E • 24°N–31°N
          </span>
          <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono font-semibold ${
            dataMode === 'CACHED_VERIFIED'
              ? 'bg-amber-50 text-amber-800 border border-amber-200'
              : dataMode === 'LIVE_MODEL'
              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
              : dataMode === 'DATA_PENDING'
              ? 'bg-slate-50 text-slate-600 border border-slate-200'
              : 'bg-amber-50 text-amber-800 border border-amber-200'
          }`}>
            {dataMode === 'CACHED_VERIFIED'
              ? 'ILLUSTRATIVE CENTROIDS'
              : dataMode === 'LIVE_MODEL'
              ? 'LIVE NWP CENTROIDS'
              : dataMode === 'DATA_PENDING'
              ? 'DATA PENDING'
              : 'DEMO DATA'}
          </span>
        </div>

        <div className="flex items-center space-x-2">
          {/* Layer Quick Selector */}
          <div className="flex bg-slate-100 p-1 rounded-xl border border-slate-200 text-[11px]">
            {(
              [
                { id: 'flood', label: 'Flood Risk' },
                { id: 'drought', label: 'Drought Risk' },
                { id: 'rainfall', label: 'Rainfall Anomaly' },
                { id: 'elevation', label: 'Elevation' },
              ] as const
            ).map((l) => (
              <button
                key={l.id}
                onClick={() => setActiveMapLayer(l.id)}
                className={`px-2 py-0.5 rounded-lg font-semibold transition ${
                  activeMapLayer === l.id
                    ? 'bg-cyan-500 text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {l.label}
              </button>
            ))}
          </div>

          {/* Zoom Buttons */}
          <div className="flex items-center space-x-1 bg-slate-100 p-1 rounded-xl border border-slate-200">
            <button
              onClick={() => setZoomLevel((prev) => Math.min(prev + 0.15, 1.6))}
              className="p-1 rounded text-slate-600 hover:text-slate-900 hover:bg-white transition"
              title="Zoom In"
              aria-label="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setZoomLevel((prev) => Math.max(prev - 0.15, 0.85))}
              className="p-1 rounded text-slate-600 hover:text-slate-900 hover:bg-white transition"
              title="Zoom Out"
              aria-label="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setZoomLevel(1)}
              className="p-1 rounded text-slate-600 hover:text-slate-900 hover:bg-white transition"
              title="Reset Zoom"
              aria-label="Reset Zoom"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Geometry Status & Data Freshness Disclosure */}
      <div className="my-1.5 px-3 py-1 rounded-xl bg-slate-50 border border-slate-200 text-[10px] text-slate-600 flex items-center justify-between">
        <span className="flex items-center gap-1.5">
          <Info className="w-3 h-3 text-blue-600 shrink-0" />
          <span>
            <strong>Cartographic Mode:</strong> Centroid points (WGS84). Detailed polygon boundaries unintegrated in prototype. Markers do not imply uniform ground truth.
          </span>
        </span>
        <span className="font-mono text-blue-700 font-semibold hidden lg:inline">EPSG:4326</span>
      </div>

      {/* Interactive Map Visual Stage */}
      <div className="relative flex-1 flex items-center justify-center my-3 overflow-hidden bg-[#f1f5f9] rounded-xl border border-slate-200 shadow-inner">
        <div
          style={{ transform: `scale(${zoomLevel})` }}
          className="relative w-full h-[290px] max-w-[540px] transition-transform duration-300 ease-out"
        >
          <svg viewBox="0 0 500 320" className="w-full h-full drop-shadow-sm select-none">
            <defs>
              <pattern id="gisGrid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#e2e8f0" strokeWidth="0.75" />
              </pattern>
              <linearGradient id="upBaseGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#ffffff" stopOpacity="0.95" />
                <stop offset="50%" stopColor="#f8fafc" stopOpacity="0.95" />
                <stop offset="100%" stopColor="#f1f5f9" stopOpacity="0.95" />
              </linearGradient>
            </defs>

            {/* GIS Lat/Long Grid Canvas */}
            <rect width="100%" height="100%" fill="url(#gisGrid)" />

            {/* Base Extrusion Shadow */}
            <path
              d="M 100 45 L 180 62 L 260 70 L 330 85 L 430 110 L 465 145 L 440 195 L 400 230 L 330 260 L 230 270 L 160 240 L 120 180 L 85 120 Z"
              fill="#cbd5e1"
              opacity="0.5"
              transform="translate(0, 6)"
            />

            {/* UP State Outer Boundary */}
            <path
              d="M 100 45 L 180 62 L 260 70 L 330 85 L 430 110 L 465 145 L 440 195 L 400 230 L 330 260 L 230 270 L 160 240 L 120 180 L 85 120 Z"
              fill="url(#upBaseGradient)"
              stroke="#64748b"
              strokeWidth="1.5"
              strokeDasharray={activeMapLayer === 'elevation' ? 'none' : 'none'}
            />

            {/* Eastern Terai Flood Susceptibility Zone (Gorakhpur / Kushinagar) */}
            <path
              d="M 360 115 L 450 135 L 440 185 L 365 170 Z"
              fill={activeMapLayer === 'flood' ? '#fee2e2' : '#e0f2fe'}
              fillOpacity={0.65}
              stroke={activeMapLayer === 'flood' ? '#dc2626' : '#0284c7'}
              strokeWidth="1.5"
              strokeDasharray="4 2"
              className={activeMapLayer === 'flood' ? 'animate-pulse cursor-pointer' : 'cursor-pointer'}
              onClick={() => handleDistrictClick(UP_DISTRICTS_DATA[0])}
            />
            <text x="375" y="155" fill="#0369a1" fontSize="7.5" fontStyle="italic" fontWeight="600" opacity="0.75" pointerEvents="none">
              TERAI ALLUVIAL PLAIN (ILLUSTRATIVE)
            </text>

            {/* Southern Bundelkhand Drought Zone (Mahoba / Jhansi / Banda) */}
            <path
              d="M 160 195 L 260 210 L 235 265 L 150 235 Z"
              fill={activeMapLayer === 'drought' ? '#fef3c7' : '#fef9c3'}
              fillOpacity={0.65}
              stroke={activeMapLayer === 'drought' ? '#d97706' : '#ca8a04'}
              strokeWidth="1.5"
              strokeDasharray="4 2"
              className="cursor-pointer"
              onClick={() => handleDistrictClick(UP_DISTRICTS_DATA[1])}
            />
            <text x="165" y="235" fill="#92400e" fontSize="7.5" fontStyle="italic" fontWeight="600" opacity="0.75" pointerEvents="none">
              BUNDELKHAND PLATEAU (ILLUSTRATIVE)
            </text>

            {/* River Lines with Cartographic Labels */}
            {/* Rapti River */}
            <path
              d="M 330 95 Q 390 135 445 160"
              fill="none"
              stroke="#0284c7"
              strokeWidth="2.5"
              strokeDasharray="4 2"
              opacity="0.85"
            />
            <text x="365" y="112" fill="#0284c7" fontSize="7.5" fontWeight="600" opacity="0.85" transform="rotate(22, 365, 112)" pointerEvents="none">
              Rapti River
            </text>

            {/* Ganga River */}
            <path
              d="M 120 70 Q 220 130 310 160 T 435 210"
              fill="none"
              stroke="#0369a1"
              strokeWidth="2.5"
              opacity="0.8"
            />
            <text x="230" y="125" fill="#0369a1" fontSize="7.5" fontWeight="600" opacity="0.8" transform="rotate(15, 230, 125)" pointerEvents="none">
              Ganga (Ganges)
            </text>

            {/* Yamuna River */}
            <path
              d="M 90 90 Q 180 160 270 190 T 370 215"
              fill="none"
              stroke="#0ea5e9"
              strokeWidth="1.8"
              opacity="0.75"
            />
            <text x="180" y="165" fill="#0ea5e9" fontSize="7" fontWeight="600" opacity="0.8" transform="rotate(18, 180, 165)" pointerEvents="none">
              Yamuna River
            </text>

            {/* District Geospatial Points & Nodes */}
            {UP_DISTRICTS_DATA.map((d) => {
              const { x, y } = getCoordinates(d.lat, d.lng);
              const isSelected = selectedLocation === d.id;
              const fillColor = getDistrictFill(d);

              return (
                <g
                  key={d.id}
                  className="cursor-pointer transition-transform focus:outline-none"
                  tabIndex={0}
                  role="button"
                  aria-label={`${d.name} (${d.hindiName}): ${
                    activeMapLayer === 'flood'
                      ? `Flood Risk ${d.floodRisk}`
                      : activeMapLayer === 'drought'
                      ? `Drought Risk ${d.droughtRisk}`
                      : `${d.anomalyPct}% anomaly`
                  }`}
                  onClick={() => handleDistrictClick(d)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      handleDistrictClick(d);
                    }
                  }}
                  onMouseEnter={() => setHoveredDistrict(d)}
                  onMouseLeave={() => setHoveredDistrict(null)}
                >
                  {/* Selected Location Target Reticle */}
                  {isSelected && (
                    <g pointerEvents="none">
                      <circle
                        cx={x}
                        cy={y}
                        r={d.isPilot ? 16 : 12}
                        fill="none"
                        stroke="#2563eb"
                        strokeWidth="2"
                        strokeDasharray="4 2"
                      />
                      <circle
                        cx={x}
                        cy={y}
                        r={d.isPilot ? 20 : 15}
                        fill="none"
                        stroke="#2563eb"
                        strokeWidth="0.75"
                        opacity="0.5"
                      />
                      <line x1={x - (d.isPilot ? 22 : 17)} y1={y} x2={x - (d.isPilot ? 12 : 8)} y2={y} stroke="#2563eb" strokeWidth="1.5" />
                      <line x1={x + (d.isPilot ? 12 : 8)} y1={y} x2={x + (d.isPilot ? 22 : 17)} y2={y} stroke="#2563eb" strokeWidth="1.5" />
                      <line x1={x} y1={y - (d.isPilot ? 22 : 17)} x2={x} y2={y - (d.isPilot ? 12 : 8)} stroke="#2563eb" strokeWidth="1.5" />
                      <line x1={x} y1={y + (d.isPilot ? 12 : 8)} x2={x} y2={y + (d.isPilot ? 22 : 17)} stroke="#2563eb" strokeWidth="1.5" />
                    </g>
                  )}

                  {/* Subtle Node Circle */}
                  <circle
                    cx={x}
                    cy={y}
                    r={d.isPilot ? (isSelected ? 9 : 7) : 4}
                    fill={fillColor}
                    stroke={isSelected ? '#0f172a' : '#ffffff'}
                    strokeWidth={isSelected ? 2 : 1}
                    className={d.isPilot ? 'drop-shadow-sm' : ''}
                  />

                  {/* Pulsing ring for pilot districts */}
                  {d.isPilot && (
                    <circle
                      cx={x}
                      cy={y}
                      r="12"
                      fill="none"
                      stroke={fillColor}
                      strokeWidth="1.5"
                      opacity="0.5"
                      className="animate-ping"
                    />
                  )}

                  {/* Label */}
                  <text
                    x={x}
                    y={y - (d.isPilot ? 11 : 6)}
                    textAnchor="middle"
                    fill={d.isPilot ? '#0f172a' : '#64748b'}
                    fontSize={d.isPilot ? '11px' : '9px'}
                    fontWeight={d.isPilot ? 'bold' : 'normal'}
                    className="select-none pointer-events-none drop-shadow-sm"
                  >
                    {d.name}
                  </text>
                </g>
              );
            })}
          </svg>

          {/* Interactive Tooltip Card on Hover */}
          {hoveredDistrict && (
            <div
              className="absolute pointer-events-none z-30 p-2.5 rounded-xl bg-white border border-slate-200 shadow-xl text-xs space-y-1 transform -translate-x-1/2 -translate-y-full"
              style={{
                left: `${((hoveredDistrict.lng - 77.0) / 7.8) * 88 + 6}%`,
                top: `${((30.5 - hoveredDistrict.lat) / 6.7) * 82 + 8}%`,
              }}
            >
              <div className="flex items-center justify-between gap-3">
                <span className="font-bold text-slate-900 text-sm">{hoveredDistrict.name}</span>
                <span
                  className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase ${
                    hoveredDistrict.floodRisk === 'high'
                      ? 'bg-rose-50 text-rose-700'
                      : hoveredDistrict.droughtRisk === 'moderate'
                      ? 'bg-amber-50 text-amber-800'
                      : 'bg-emerald-50 text-emerald-800'
                  }`}
                >
                  {activeMapLayer === 'flood'
                    ? `Flood: ${hoveredDistrict.floodRisk}`
                    : activeMapLayer === 'drought'
                    ? `Drought: ${hoveredDistrict.droughtRisk}`
                    : `${hoveredDistrict.anomalyPct}% Anomaly`}
                </span>
              </div>
              <div className="text-[9px] text-amber-700 font-medium">
                Centroid Baseline • Illustrative Sample
              </div>
              <div className="text-[10px] text-slate-500 font-mono">
                {hoveredDistrict.lat.toFixed(4)}°N, {hoveredDistrict.lng.toFixed(4)}°E
              </div>
              <div className="text-[10px] text-blue-700 font-medium">
                Basin: {hoveredDistrict.riverBasin}
              </div>
              <div className="text-[10px] text-slate-600">
                Elevation: {hoveredDistrict.elevationM} m MSL
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer Legend and Disclosures with Dual Visual Encoding */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-200 text-xs">
        <div className="flex flex-wrap items-center gap-3 text-[11px]">
          <div className="flex items-center space-x-1.5" title="Category: High Risk (Score >= 70 or Anomaly > +50%)">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-600 ring-2 ring-rose-100 flex items-center justify-center text-[7px] text-white font-bold">
              H
            </span>
            <span className="text-slate-700 font-medium">● High Risk</span>
          </div>
          <div className="flex items-center space-x-1.5" title="Category: Moderate Risk (SPI-3 < -1.5 or Anomaly 20-50%)">
            <span className="w-2.5 h-2.5 rounded-sm bg-amber-500 ring-2 ring-amber-100 flex items-center justify-center text-[7px] text-white font-bold">
              M
            </span>
            <span className="text-slate-700 font-medium">▲ Moderate</span>
          </div>
          <div className="flex items-center space-x-1.5" title="Category: Normal / Low Risk">
            <span className="w-2.5 h-2.5 rounded-none bg-blue-600 ring-2 ring-blue-100 flex items-center justify-center text-[7px] text-white font-bold">
              L
            </span>
            <span className="text-slate-700 font-medium">■ Normal / Baseline</span>
          </div>
          <div className="flex items-center space-x-1.5" title="No verified sensor data">
            <span className="w-2.5 h-2.5 rounded-full border border-dashed border-slate-400" />
            <span className="text-slate-500 font-medium">○ No Data</span>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-[10px] text-slate-500 font-mono hidden xl:inline">
            Attribution: OpenStreetMap • NASA SRTM 30m • NASA GPM IMERG 0.1°
          </span>
          <button
            onClick={() => setCurrentRoute('map')}
            className="inline-flex items-center space-x-1 px-3 py-1 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 transition text-xs font-semibold"
          >
            <span>Full Map Explorer</span>
            <ExternalLink className="w-3 h-3" />
          </button>
        </div>
      </div>
    </div>
  );
};
