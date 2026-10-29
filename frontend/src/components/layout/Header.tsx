import React, { useState } from 'react';
import {
  Search,
  Calendar,
  Bell,
  Menu,
  ShieldAlert,
  ChevronDown,
  Activity,
  AlertCircle,
  RefreshCw,
  Sliders,
  CheckCircle2,
} from 'lucide-react';
import { useApp, PILOT_LOCATIONS, DataFreshnessMode } from '../../context/AppContext';
import { PilotLocationId } from '../../types';

export const Header: React.FC = () => {
  const {
    setIsSidebarOpen,
    setIsSearchOpen,
    setIsNotificationsOpen,
    selectedLocation,
    setSelectedLocation,
    themeMode,
    dataFreshnessMode,
    setDataFreshnessMode,
  } = useApp();

  const [showStatusMenu, setShowStatusMenu] = useState(false);

  return (
    <header className="sticky top-0 z-30 w-full px-4 lg:px-8 py-3.5 bg-navy-950/85 backdrop-blur-md border-b border-navy-700/60 flex items-center justify-between gap-4">
      {/* Left Section: Mobile Menu + Search bar */}
      <div className="flex items-center space-x-3 flex-1 max-w-xl">
        <button
          onClick={() => setIsSidebarOpen(true)}
          className="lg:hidden p-2 rounded-xl text-slate-300 hover:text-white bg-navy-850 hover:bg-navy-800 border border-navy-700 interactive-btn"
          aria-label="Open Navigation"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Global Search Bar (opens search modal) */}
        <button
          onClick={() => setIsSearchOpen(true)}
          className="w-full flex items-center justify-between px-4 py-2 rounded-xl bg-navy-850/90 hover:bg-navy-800 text-slate-400 hover:text-slate-200 border border-navy-700/70 hover:border-cyan-500/50 shadow-inner transition-all duration-200 group interactive-btn"
        >
          <div className="flex items-center space-x-2.5 text-sm">
            <Search className="w-4 h-4 text-slate-400 group-hover:text-cyan-400 transition-colors" />
            <span className="truncate">Search location (e.g., Gorakhpur, Mahoba)...</span>
          </div>
          <kbd className="hidden sm:inline-flex items-center gap-1 text-[11px] font-mono font-medium px-2 py-0.5 rounded bg-navy-900 border border-navy-700 text-slate-400 shadow-sm">
            ⌘K
          </kbd>
        </button>
      </div>

      {/* Right Section: Pilot Selector, Demo Data Pill, Live Timestamp, Notifications, Profile */}
      <div className="flex items-center space-x-2.5">
        {/* Pilot Location Switcher Pill */}
        <div className="hidden md:flex items-center p-1 rounded-xl bg-navy-900/90 border border-navy-700/80 shadow-inner">
          {(['gorakhpur', 'mahoba', 'all'] as PilotLocationId[]).map((locId) => {
            const loc = PILOT_LOCATIONS[locId];
            const isSelected = selectedLocation === locId;
            return (
              <button
                key={locId}
                onClick={() => setSelectedLocation(locId)}
                className={`px-3 py-1 text-xs font-semibold rounded-lg transition-all duration-200 ${
                  isSelected
                    ? loc.focusType === 'flood'
                      ? 'bg-gradient-to-r from-sky-500 to-blue-600 text-white shadow-sm ring-1 ring-cyan-400/50'
                      : loc.focusType === 'drought'
                      ? 'bg-gradient-to-r from-amber-500 to-orange-600 text-white shadow-sm ring-1 ring-amber-400/50'
                      : 'bg-navy-700 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-navy-800/60'
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
            className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-xl bg-navy-850 border border-navy-700 text-xs hover:border-cyan-500/50 transition interactive-btn"
            title="Click to simulate data pipeline states (Fresh / Stale / Loading / Error)"
          >
            <span
              className={`w-2 h-2 rounded-full ${
                dataFreshnessMode === 'fresh'
                  ? 'bg-emerald-400 animate-pulse'
                  : dataFreshnessMode === 'stale'
                  ? 'bg-amber-400'
                  : dataFreshnessMode === 'loading'
                  ? 'bg-cyan-400 animate-ping'
                  : 'bg-rose-500'
              }`}
            />
            <span className="font-mono text-[11px] text-slate-300 capitalize hidden sm:inline">
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
            <div className="absolute right-0 mt-2 w-56 p-2 rounded-xl bg-navy-900 border border-navy-700 shadow-2xl z-50 text-xs">
              <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-400 border-b border-navy-800">
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
                        ? 'bg-cyan-500/20 text-cyan-300 font-semibold'
                        : 'text-slate-300 hover:bg-navy-800'
                    }`}
                  >
                    <div>{opt.label}</div>
                    <div className="text-[10px] text-slate-400 leading-tight">{opt.desc}</div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Live Date / Timestamp Badge */}
        <div className="hidden xl:flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-navy-850/80 border border-navy-700/80 text-xs text-slate-300">
          <Calendar className="w-3.5 h-3.5 text-cyan-400" />
          <span className="font-mono text-[11px]">28 Oct 2026, 10:30 AM</span>
        </div>

        {/* Notifications Alert Bell */}
        <button
          onClick={() => setIsNotificationsOpen(true)}
          className="relative p-2 rounded-xl bg-navy-850 hover:bg-navy-800 text-slate-300 hover:text-white border border-navy-700/80 interactive-btn"
          aria-label="Alerts & Updates"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-rose-500 ring-2 ring-navy-950 animate-pulse" />
        </button>

        {/* Profile / Role Badge */}
        <div className="flex items-center space-x-2 pl-1">
          <div
            className="w-8 h-8 rounded-xl bg-gradient-to-tr from-slate-700 to-slate-600 border border-slate-500/40 flex items-center justify-center font-bold text-xs text-white shadow-md cursor-default"
            title="Role: Environmental Analyst / Pilot Responder"
          >
            R
          </div>
        </div>
      </div>
    </header>
  );
};
