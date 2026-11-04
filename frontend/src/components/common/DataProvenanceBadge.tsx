import React, { useState } from 'react';
import { ShieldCheck, Database, AlertCircle, Clock, Info, CheckCircle2, ChevronDown, ChevronUp, Activity } from 'lucide-react';
import type { DataMode } from '../../types';

export interface DataProvenanceBadgeProps {
  mode?: DataMode | string;
  source?: string;
  datasetVersion?: string;
  spatialResolution?: string;
  observationPeriod?: string;
  lastUpdated?: string;
  qualityStatus?: string;
  limitations?: string;
  compact?: boolean;
}

export const DataProvenanceBadge: React.FC<DataProvenanceBadgeProps> = ({
  mode = 'CACHED_VERIFIED',
  source = 'CHIRPS v2.0 / NASA GPM Late Run',
  datasetVersion = 'v2.0',
  spatialResolution = '0.05° (~5.3 km)',
  observationPeriod = '1991–2026 Reference Period',
  lastUpdated = '28 Oct 2026, 10:30 AM',
  qualityStatus = 'verified',
  limitations = 'Spatial intersection bounded to official administrative polygon. Meteorological metrics do not calculate river discharge.',
  compact = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  // Normalize mode
  const cleanMode = (mode || '').toUpperCase().trim();
  let label = 'CACHED VERIFIED DATA';
  let badgeStyle = 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30 hover:bg-cyan-500/25';
  let dotColor = 'bg-cyan-400';
  let icon = <ShieldCheck className="w-3.5 h-3.5 mr-1 text-cyan-400" />;

  if (cleanMode === 'HISTORICAL_MODEL_ESTIMATE' || cleanMode.includes('HISTORICAL_MODEL')) {
    label = 'HISTORICAL MODEL ESTIMATE';
    badgeStyle = 'bg-sky-500/15 text-sky-300 border-sky-500/30 hover:bg-sky-500/25';
    dotColor = 'bg-sky-400';
    icon = <Database className="w-3.5 h-3.5 mr-1 text-sky-400" />;
  } else if (cleanMode === 'LIVE_MODEL_ESTIMATE' || cleanMode.includes('LIVE_MODEL_ESTIMATE')) {
    label = 'LIVE MODEL ESTIMATE';
    badgeStyle = 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30 hover:bg-emerald-500/25';
    dotColor = 'bg-emerald-400 animate-pulse';
    icon = <Activity className="w-3.5 h-3.5 mr-1 text-emerald-400" />;
  } else if (cleanMode === 'MIXED_MODEL_ESTIMATE' || cleanMode.includes('MIXED_MODEL')) {
    label = 'MIXED MODEL ESTIMATE';
    badgeStyle = 'bg-teal-500/15 text-teal-300 border-teal-500/30 hover:bg-teal-500/25';
    dotColor = 'bg-teal-400';
    icon = <Activity className="w-3.5 h-3.5 mr-1 text-teal-400" />;
  } else if (cleanMode === 'MODEL_DERIVED' || cleanMode.includes('MODEL_DERIVED')) {
    label = 'MODEL DERIVED';
    badgeStyle = 'bg-blue-500/15 text-blue-300 border-blue-500/30 hover:bg-blue-500/25';
    dotColor = 'bg-blue-400';
    icon = <Activity className="w-3.5 h-3.5 mr-1 text-blue-400" />;
  } else if (cleanMode === 'LIVE_MODEL' || cleanMode.includes('LIVE_MODEL')) {
    label = 'LIVE MODEL DATA';
    badgeStyle = 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30 hover:bg-emerald-500/25';
    dotColor = 'bg-emerald-400 animate-pulse';
    icon = <Activity className="w-3.5 h-3.5 mr-1 text-emerald-400" />;
  } else if (cleanMode.includes('LIVE')) {
    label = 'LIVE VERIFIED DATA';
    badgeStyle = 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30 hover:bg-emerald-500/25';
    dotColor = 'bg-emerald-400 animate-pulse';
    icon = <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-400" />;
  } else if (cleanMode.includes('PROVIDER_ERROR') || cleanMode.includes('ERROR')) {
    label = 'PROVIDER ERROR';
    badgeStyle = 'bg-rose-500/15 text-rose-300 border-rose-500/30 hover:bg-rose-500/25';
    dotColor = 'bg-rose-400';
    icon = <AlertCircle className="w-3.5 h-3.5 mr-1 text-rose-400" />;
  } else if (cleanMode.includes('FORECAST')) {
    label = 'NWP FORECAST';
    badgeStyle = 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30 hover:bg-indigo-500/25';
    dotColor = 'bg-indigo-400';
    icon = <Activity className="w-3.5 h-3.5 mr-1 text-indigo-400" />;
  } else if (cleanMode.includes('DEMO')) {
    label = 'DEMO DATA';
    badgeStyle = 'bg-amber-500/15 text-amber-300 border-amber-500/30 hover:bg-amber-500/25';
    dotColor = 'bg-amber-400';
    icon = <Info className="w-3.5 h-3.5 mr-1 text-amber-400" />;
  } else if (cleanMode.includes('PENDING')) {
    label = 'DATA PENDING';
    badgeStyle = 'bg-slate-700/40 text-slate-300 border-slate-600/40 hover:bg-slate-700/60';
    dotColor = 'bg-slate-400';
    icon = <Clock className="w-3.5 h-3.5 mr-1 text-slate-400" />;
  } else if (cleanMode.includes('STALE')) {
    label = 'DATA STALE';
    badgeStyle = 'bg-orange-500/15 text-orange-300 border-orange-500/30 hover:bg-orange-500/25';
    dotColor = 'bg-orange-400';
    icon = <AlertCircle className="w-3.5 h-3.5 mr-1 text-orange-400" />;
  } else if (cleanMode.includes('MANUAL') || cleanMode.includes('UPLOAD')) {
    label = 'MANUAL UPLOAD';
    badgeStyle = 'bg-purple-500/15 text-purple-300 border-purple-500/30 hover:bg-purple-500/25';
    dotColor = 'bg-purple-400';
    icon = <Database className="w-3.5 h-3.5 mr-1 text-purple-400" />;
  }

  return (
    <div className="inline-block relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold tracking-wide border transition-colors cursor-pointer select-none ${badgeStyle}`}
        title="Click to view data provenance and scientific metadata"
      >
        <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${dotColor}`} />
        {icon}
        <span>{label}</span>
        {!compact && (
          isOpen ? (
            <ChevronUp className="w-3 h-3 ml-1.5 opacity-70" />
          ) : (
            <ChevronDown className="w-3 h-3 ml-1.5 opacity-70" />
          )
        )}
      </button>

      {/* Expandable Provenance Disclosure Card */}
      {isOpen && (
        <div className="absolute left-0 mt-2 z-50 w-80 p-3.5 rounded-xl bg-white border border-slate-200 shadow-xl text-left text-xs space-y-2 animate-in fade-in zoom-in-95 duration-150">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <span className="font-bold text-slate-900 flex items-center">
              <Database className="w-3.5 h-3.5 mr-1.5 text-blue-600" />
              Dataset Provenance
            </span>
            <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono border ${badgeStyle}`}>
              {label}
            </span>
          </div>

          <div className="space-y-1.5 text-[11px] text-slate-600">
            <div className="flex justify-between">
              <span className="text-slate-500">Data Source:</span>
              <span className="font-medium text-slate-800">{source}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Dataset Version:</span>
              <span className="font-mono text-blue-600 font-semibold">{datasetVersion}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Spatial Resolution:</span>
              <span className="font-medium text-slate-800">{spatialResolution}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Observation Window:</span>
              <span className="font-medium text-slate-800">{observationPeriod}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Quality Status:</span>
              <span className="capitalize font-mono font-semibold text-emerald-600">{qualityStatus}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Last Synced:</span>
              <span className="text-slate-800">{lastUpdated}</span>
            </div>
          </div>

          {limitations && (
            <div className="pt-2 border-t border-slate-100 text-[10px] text-slate-500 leading-relaxed">
              <span className="font-semibold text-amber-700 block mb-0.5">Scientific Boundary Notice:</span>
              {limitations}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
