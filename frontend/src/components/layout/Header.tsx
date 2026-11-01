import React, { useState } from 'react';
import {
  Search,
  Calendar,
  Bell,
  Menu,
  ChevronDown,
} from 'lucide-react';
import { useApp, PILOT_LOCATIONS, DataFreshnessMode } from '../../context/AppContext';
import { PilotLocationId } from '../../types';
import { RegionSelector } from '../common/RegionSelector';
import { DataProvenanceBadge } from '../common/DataProvenanceBadge';

export const Header: React.FC = () => {
  const {
    setIsSidebarOpen,
    setIsSearchOpen,
    setIsNotificationsOpen,
    selectedLocation,
    setSelectedLocation,
    dataMode,
    dataFreshnessMode,
    setDataFreshnessMode,
  } = useApp();

  const [showStatusMenu, setShowStatusMenu] = useState(false);

  return (
    <header className="sticky top-0 z-30 w-full px-3 sm:px-4 lg:px-6 py-2.5 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-xs flex items-center justify-between gap-2 sm:gap-3 min-w-0">
      {/* Left Section: Mobile Menu + Search bar */}
      <div className="flex items-center space-x-2 sm:space-x-3 flex-1 min-w-0 max-w-xs sm:max-w-sm md:max-w-md">
        <button
          onClick={() => setIsSidebarOpen(true)}
          className="lg:hidden p-1.5 sm:p-2 rounded-lg text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 border border-slate-200 interactive-btn shrink-0"
          aria-label="Open Navigation"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Global Search Bar (opens search modal) */}
        <button
          onClick={() => setIsSearchOpen(true)}
          className="w-full flex items-center justify-between px-3 py-1.5 rounded-lg bg-slate-50 hover:bg-white text-slate-500 hover:text-slate-800 border border-slate-200 hover:border-slate-300 shadow-inner transition-all duration-150 group interactive-btn min-w-0"
        >
          <div className="flex items-center space-x-2 text-xs sm:text-sm min-w-0">
            <Search className="w-4 h-4 text-slate-400 group-hover:text-blue-600 transition-colors shrink-0" />
            <span className="truncate">Search location (e.g., Gorakhpur, Mahoba)...</span>
          </div>
          <kbd className="hidden sm:inline-flex items-center gap-1 text-[10px] font-mono font-medium px-1.5 py-0.5 rounded bg-white border border-slate-200 text-slate-500 shadow-xs shrink-0">
            ⌘K
          </kbd>
        </button>
      </div>

      {/* Right Section: Multi-Region Selector, Pilot Switcher, Integrity Pill, Profile */}
      <div className="flex items-center space-x-1.5 sm:space-x-2 shrink-0">
        {/* Dynamic Multi-Region District Selector */}
        <RegionSelector />

        {/* Global Data Mode & Provenance Badge */}
        <div className="hidden 2xl:inline-flex">
          <DataProvenanceBadge mode={dataMode} compact />
        </div>

        {/* Pilot Location Switcher Pill (Visible on xl+ screens where width is plentiful) */}
        <div className="hidden xl:flex items-center p-0.5 rounded-lg bg-slate-100 border border-slate-200">
          {(['gorakhpur', 'mahoba', 'all'] as PilotLocationId[]).map((locId) => {
            const loc = PILOT_LOCATIONS[locId];
            const isSelected = selectedLocation === locId;
            return (
              <button
                key={locId}
                onClick={() => setSelectedLocation(locId)}
                className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all duration-150 ${
                  isSelected
                    ? loc.focusType === 'flood'
                      ? 'bg-sky-600 text-white shadow-xs'
                      : loc.focusType === 'drought'
                      ? 'bg-amber-600 text-white shadow-xs'
                      : 'bg-slate-800 text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                }`}
              >
                {loc.name.split(' ')[0]}
              </button>
            );
          })}
        </div>

        {/* Demo Data / Integrity Pill with Dropdown state simulator */}
        <div className="relative">
          <button
            onClick={() => setShowStatusMenu((prev) => !prev)}
            className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-700 hover:border-slate-300 transition interactive-btn"
            title="Click to simulate data pipeline states (Fresh / Stale / Loading / Error)"
          >
            <span
              className={`w-2 h-2 rounded-full ${
                dataFreshnessMode === 'fresh'
                  ? 'bg-emerald-500 animate-pulse'
                  : dataFreshnessMode === 'stale'
                  ? 'bg-amber-500'
                  : dataFreshnessMode === 'loading'
                  ? 'bg-sky-500 animate-ping'
                  : 'bg-rose-500'
              }`}
            />
            <span className="font-mono text-[11px] text-slate-700 capitalize hidden sm:inline">
              {dataFreshnessMode === 'fresh'
                ? 'Demo Data'
                : dataFreshnessMode === 'stale'
                ? 'Stale (>24h)'
                : dataFreshnessMode === 'loading'
                ? 'Fetching...'
                : 'Data Error'}
            </span>
            <ChevronDown className="w-3 h-3 text-slate-400" />
          </button>

          {showStatusMenu && (
            <div className="absolute right-0 mt-2 w-56 p-2 rounded-xl bg-white border border-slate-200 shadow-xl z-50 text-xs">
              <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-100">
                Data Pipeline State Simulation
              </div>
              <div className="mt-1 space-y-1">
                {(
                  [
                    { mode: 'fresh', label: 'Fresh Data (28 Oct 2026)', desc: 'Normal verified operational state' },
                    { mode: 'stale', label: 'Stale Data State', desc: 'Simulate delayed ingest (>24h lag)' },
                    { mode: 'loading', label: 'Loading / Ingesting', desc: 'Simulate telemetry ingestion state' },
                    { mode: 'error', label: 'Pipeline Error State', desc: 'Simulate missing or degraded feed' },
                  ] as const
                ).map((opt) => (
                  <button
                    key={opt.mode}
                    onClick={() => {
                      setDataFreshnessMode(opt.mode as DataFreshnessMode);
                      setShowStatusMenu(false);
                    }}
                    className={`w-full text-left p-2 rounded-lg transition ${
                      dataFreshnessMode === opt.mode
                        ? 'bg-blue-50 text-blue-700 font-semibold'
                        : 'text-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    <div className="font-medium">{opt.label}</div>
                    <div className="text-[10px] text-slate-500 leading-tight">{opt.desc}</div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Live Date / Timestamp Badge */}
        <div className="hidden xl:flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-600">
          <Calendar className="w-3.5 h-3.5 text-blue-600" />
          <span className="font-mono text-[11px]">28 Oct 2026, 10:30 AM</span>
        </div>

        {/* Notifications Alert Bell */}
        <button
          onClick={() => setIsNotificationsOpen(true)}
          className="relative p-2 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-600 hover:text-slate-900 border border-slate-200 interactive-btn"
          aria-label="Alerts & Updates"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-rose-500 ring-2 ring-white animate-pulse" />
        </button>

        {/* Role Badge */}
        <div className="flex items-center pl-1">
          <div
            className="w-8 h-8 rounded-lg bg-blue-600 text-white font-bold text-xs flex items-center justify-center shadow-xs cursor-default"
            title="Role: Environmental Intelligence Officer"
          >
            R
          </div>
        </div>
      </div>
    </header>
  );
};
