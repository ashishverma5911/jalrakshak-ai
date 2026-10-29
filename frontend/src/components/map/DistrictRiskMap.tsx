import React, { useState } from 'react';
import {
  ZoomIn,
  ZoomOut,
  Layers,
  MapPin,
  ExternalLink,
  Navigation,
  Info,
  Maximize2,
  RotateCcw,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { UP_DISTRICTS_DATA, DistrictGeoData, DEMO_DATA_DISCLAIMER } from '../../data/mockData';

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
  } = useApp();

  const [zoomLevel, setZoomLevel] = useState(1);
  const [hoveredDistrict, setHoveredDistrict] = useState<DistrictGeoData | null>(null);
  const [viewStyle, setViewStyle] = useState<'3d' | 'geo'>('3d');

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
      if (d.floodRisk === 'high') return '#ef4444';
      if (d.floodRisk === 'moderate') return '#f59e0b';
      return '#0284c7';
    }
    if (activeMapLayer === 'drought') {
      if (d.droughtRisk === 'high') return '#ef4444';
      if (d.droughtRisk === 'moderate') return '#ea580c';
      return '#059669';
    }
    if (activeMapLayer === 'rainfall') {
      return d.anomalyPct > 20 ? '#00e5ff' : d.anomalyPct < -20 ? '#f59e0b' : '#38bdf8';
    }
    // Elevation
    return d.elevationM > 200 ? '#78350f' : d.elevationM > 100 ? '#b45309' : '#0e7490';
  };

  return (
    <div className="relative w-full h-full min-h-[340px] flex flex-col justify-between overflow-hidden rounded-2xl bg-navy-900/70 border border-navy-800 p-3.5 select-none">
      {/* Top Map Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 z-10">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          <span className="text-xs font-bold text-white tracking-wide">
            Uttar Pradesh Geospatial Risk Canvas
          </span>
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-navy-800 text-slate-400 font-mono hidden sm:inline">
            77°E–85°E • 24°N–31°N
          </span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 font-mono">
            DEMO DATA
          </span>
        </div>

        <div className="flex items-center space-x-2">
          {/* Layer Quick Selector */}
          <div className="flex bg-navy-850 p-1 rounded-xl border border-navy-750 text-[11px]">
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
                    ? 'bg-cyan-500 text-navy-950 shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {l.label}
              </button>
            ))}
          </div>

          {/* Zoom Buttons */}
          <div className="flex items-center space-x-1 bg-navy-850/80 p-1 rounded-xl border border-navy-700/60">
            <button
              onClick={() => setZoomLevel((prev) => Math.min(prev + 0.15, 1.6))}
              className="p-1 rounded text-slate-300 hover:text-white hover:bg-navy-700 transition"
              title="Zoom In"
              aria-label="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setZoomLevel((prev) => Math.max(prev - 0.15, 0.85))}
              className="p-1 rounded text-slate-300 hover:text-white hover:bg-navy-700 transition"
              title="Zoom Out"
              aria-label="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setZoomLevel(1)}
              className="p-1 rounded text-slate-300 hover:text-white hover:bg-navy-700 transition"
              title="Reset Zoom"
              aria-label="Reset Zoom"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Geometry Status & Data Freshness Disclosure */}
      <div className="my-1.5 px-3 py-1 rounded-xl bg-navy-950/80 border border-navy-800 text-[10px] text-slate-400 flex items-center justify-between">
        <span className="flex items-center gap-1.5">
          <Info className="w-3 h-3 text-cyan-400 shrink-0" />
          <span>
            <strong>Cartographic Mode:</strong> Centroid points (WGS84). Detailed polygon boundaries unintegrated in prototype. Markers do not imply uniform ground truth.
          </span>
        </span>
        <span className="font-mono text-cyan-400 hidden lg:inline">EPSG:4326</span>
      </div>

      {/* Interactive Map Visual Stage */}
      <div className="relative flex-1 flex items-center justify-center my-3 overflow-hidden">
        <div
          style={{ transform: `scale(${zoomLevel})` }}
          className="relative w-full h-[290px] max-w-[540px] transition-transform duration-300 ease-out"
        >
          <svg viewBox="0 0 500 320" className="w-full h-full drop-shadow-2xl">
            <defs>
              <linearGradient id="upBaseGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#0a2538" stopOpacity="0.9" />
                <stop offset="50%" stopColor="#0f3752" stopOpacity="0.8" />
                <stop offset="100%" stopColor="#091d2c" stopOpacity="0.9" />
              </linearGradient>
              <filter id="mapShadow3D" x="-10%" y="-10%" width="120%" height="130%">
                <feDropShadow dx="0" dy="14" stdDeviation="10" floodColor="#000000" floodOpacity="0.6" />
              </filter>
            </defs>

            {/* 3D Depth Base Extrusion */}
            <path
              d="M 100 45 L 180 62 L 260 70 L 330 85 L 430 110 L 465 145 L 440 195 L 400 230 L 330 260 L 230 270 L 160 240 L 120 180 L 85 120 Z"
              fill="#04101a"
              transform="translate(0, 12)"
            />

            {/* UP State Outer Boundary */}
            <path
              d="M 100 45 L 180 62 L 260 70 L 330 85 L 430 110 L 465 145 L 440 195 L 400 230 L 330 260 L 230 270 L 160 240 L 120 180 L 85 120 Z"
              fill="url(#upBaseGradient)"
              stroke="rgba(0, 229, 255, 0.45)"
              strokeWidth="2"
              filter="url(#mapShadow3D)"
            />

            {/* Eastern Terai Flood Susceptibility Zone (Gorakhpur / Kushinagar) */}
            <path
              d="M 360 115 L 450 135 L 440 185 L 365 170 Z"
              fill={activeMapLayer === 'flood' ? '#ef4444' : '#0369a1'}
              fillOpacity={activeMapLayer === 'flood' ? 0.75 : 0.45}
              stroke={activeMapLayer === 'flood' ? '#ef4444' : '#38bdf8'}
              strokeWidth="1.5"
              className={activeMapLayer === 'flood' ? 'animate-pulse cursor-pointer' : 'cursor-pointer'}
              onClick={() => handleDistrictClick(UP_DISTRICTS_DATA[0])}
            />

            {/* Southern Bundelkhand Drought Zone (Mahoba / Jhansi / Banda) */}
            <path
              d="M 160 195 L 260 210 L 235 265 L 150 235 Z"
              fill={activeMapLayer === 'drought' ? '#ea580c' : '#b45309'}
              fillOpacity={activeMapLayer === 'drought' ? 0.8 : 0.4}
              stroke={activeMapLayer === 'drought' ? '#f59e0b' : '#d97706'}
              strokeWidth="1.5"
              className="cursor-pointer"
              onClick={() => handleDistrictClick(UP_DISTRICTS_DATA[1])}
            />

            {/* River Lines with Tooltip Labels */}
            {/* Rapti River */}
            <path
              d="M 330 95 Q 390 135 445 160"
              fill="none"
              stroke="#00e5ff"
              strokeWidth="2.5"
              strokeDasharray="4 2"
              opacity="0.85"
            />
            {/* Ganga River */}
            <path
              d="M 120 70 Q 220 130 310 160 T 435 210"
              fill="none"
              stroke="#38bdf8"
              strokeWidth="2"
              opacity="0.7"
            />
            {/* Yamuna River */}
            <path
              d="M 90 90 Q 180 160 270 190 T 370 215"
              fill="none"
              stroke="#0284c7"
              strokeWidth="1.5"
              opacity="0.6"
            />

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
                  {/* Focus Ring Indicator */}
                  {isSelected && (
                    <circle
                      cx={x}
                      cy={y}
                      r={d.isPilot ? 15 : 10}
                      fill="none"
                      stroke="#00e5ff"
                      strokeWidth="2"
                      strokeDasharray="3 2"
                    />
                  )}

                  {/* Subtle Node Circle */}
                  <circle
                    cx={x}
                    cy={y}
                    r={d.isPilot ? (isSelected ? 9 : 7) : 4}
                    fill={fillColor}
                    stroke={isSelected ? '#ffffff' : 'rgba(255,255,255,0.7)'}
                    strokeWidth={isSelected ? 2.5 : 1}
                    className={d.isPilot ? 'drop-shadow-md' : ''}
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
                    fill={d.isPilot ? '#ffffff' : '#94a3b8'}
                    fontSize={d.isPilot ? '11px' : '9px'}
                    fontWeight={d.isPilot ? 'bold' : 'normal'}
                    className="select-none pointer-events-none drop-shadow"
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
              className="absolute pointer-events-none z-30 p-2.5 rounded-xl bg-navy-950/95 border border-cyan-500/50 shadow-2xl text-xs space-y-1 transform -translate-x-1/2 -translate-y-full"
              style={{
                left: `${((hoveredDistrict.lng - 77.0) / 7.8) * 88 + 6}%`,
                top: `${((30.5 - hoveredDistrict.lat) / 6.7) * 82 + 8}%`,
              }}
            >
              <div className="flex items-center justify-between gap-3">
                <span className="font-bold text-white text-sm">{hoveredDistrict.name}</span>
                <span
                  className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase ${
                    hoveredDistrict.floodRisk === 'high'
                      ? 'bg-rose-500/20 text-rose-300'
                      : hoveredDistrict.droughtRisk === 'moderate'
                      ? 'bg-amber-500/20 text-amber-300'
                      : 'bg-emerald-500/20 text-emerald-300'
                  }`}
                >
                  {activeMapLayer === 'flood'
                    ? `Flood: ${hoveredDistrict.floodRisk}`
                    : activeMapLayer === 'drought'
                    ? `Drought: ${hoveredDistrict.droughtRisk}`
                    : `${hoveredDistrict.anomalyPct}% Anomaly`}
                </span>
              </div>
              <div className="text-[10px] text-slate-300 font-mono">
                {hoveredDistrict.lat.toFixed(4)}°N, {hoveredDistrict.lng.toFixed(4)}°E
              </div>
              <div className="text-[10px] text-cyan-300">
                Basin: {hoveredDistrict.riverBasin}
              </div>
              <div className="text-[10px] text-slate-400">
                Elevation: {hoveredDistrict.elevationM} m MSL
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer Legend and Disclosures with Dual Visual Encoding */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-navy-800 text-xs">
        <div className="flex flex-wrap items-center gap-3 text-[11px]">
          <div className="flex items-center space-x-1.5" title="Category: High Risk (Score >= 70 or Anomaly > +50%)">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 ring-2 ring-rose-500/30 flex items-center justify-center text-[7px] text-white font-bold">
              H
            </span>
            <span className="text-slate-300 font-medium">● High Risk</span>
          </div>
          <div className="flex items-center space-x-1.5" title="Category: Moderate Risk (SPI-3 < -1.5 or Anomaly 20-50%)">
            <span className="w-2.5 h-2.5 rounded-sm bg-amber-500 ring-2 ring-amber-500/30 flex items-center justify-center text-[7px] text-navy-950 font-bold">
              M
            </span>
            <span className="text-slate-300 font-medium">▲ Moderate</span>
          </div>
          <div className="flex items-center space-x-1.5" title="Category: Normal / Low Risk">
            <span className="w-2.5 h-2.5 rounded-none bg-sky-500 ring-2 ring-sky-500/30 flex items-center justify-center text-[7px] text-white font-bold">
              L
            </span>
            <span className="text-slate-300 font-medium">■ Normal / Baseline</span>
          </div>
          <div className="flex items-center space-x-1.5" title="No verified sensor data">
            <span className="w-2.5 h-2.5 rounded-full border border-dashed border-slate-400" />
            <span className="text-slate-400 font-medium">○ No Data</span>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-[10px] text-slate-400 font-mono hidden xl:inline">
            Attribution: OpenStreetMap • NASA SRTM 30m • NASA GPM IMERG 0.1°
          </span>
          <button
            onClick={() => setCurrentRoute('map')}
            className="inline-flex items-center space-x-1 px-3 py-1 rounded-lg bg-navy-800 hover:bg-cyan-500/20 text-cyan-400 hover:text-cyan-300 border border-cyan-500/30 transition text-xs font-semibold"
          >
            <span>Full Map Explorer</span>
            <ExternalLink className="w-3 h-3" />
          </button>
        </div>
      </div>
    </div>
  );
};
