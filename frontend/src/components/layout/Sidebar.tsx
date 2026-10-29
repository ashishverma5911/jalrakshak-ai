import React from 'react';
import {
  Home,
  Droplets,
  SunMedium,
  Map,
  BarChart3,
  Sparkles,
  ShieldCheck,
  Database,
  Activity,
  X,
  Compass,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { NavigationRoute } from '../../types';

interface NavItem {
  id: NavigationRoute;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  tag?: string;
}

const NAV_ITEMS: NavItem[] = [
  { id: 'dashboard', label: 'Dashboard', icon: Home },
  { id: 'flood', label: 'Flood Assessment', icon: Droplets },
  { id: 'drought', label: 'Drought Assessment', icon: SunMedium },
  { id: 'map', label: 'Risk Map', icon: Map },
  { id: 'trends', label: 'Rainfall & Trends', icon: BarChart3 },
  { id: 'assistant', label: 'AI Assistant', icon: Sparkles, tag: 'Gemma 4' },
  { id: 'preparedness', label: 'Preparedness', icon: ShieldCheck },
  { id: 'sources', label: 'Data Sources', icon: Database },
  { id: 'monitoring', label: 'System Monitoring', icon: Activity },
];

export const Sidebar: React.FC = () => {
  const { currentRoute, setCurrentRoute, isSidebarOpen, setIsSidebarOpen } = useApp();

  const handleNavClick = (id: NavigationRoute) => {
    setCurrentRoute(id);
    if (window.innerWidth < 1024) {
      setIsSidebarOpen(false);
    }
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Main Sidebar Panel */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 w-64 bg-white/95 backdrop-blur-md border-r border-slate-200/90 shadow-xl flex flex-col justify-between transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          isSidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand Header */}
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => handleNavClick('dashboard')}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-md shadow-sky-500/20 text-white">
              <Droplets className="w-6 h-6 fill-white/20 stroke-white" />
            </div>
            <div>
              <div className="font-extrabold text-slate-900 tracking-tight text-xl leading-tight">
                <span>JalRakshak</span>
              </div>
              <p className="text-xs text-slate-500 font-medium tracking-wide">For Safer Communities</p>
            </div>
          </div>

          <button
            onClick={() => setIsSidebarOpen(false)}
            className="lg:hidden p-1.5 text-slate-400 hover:text-slate-700 rounded-lg"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = currentRoute === item.id;

            return (
              <button
                key={item.id}
                onClick={() => handleNavClick(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl font-medium text-sm transition-all duration-200 interactive-btn ${
                  isActive
                    ? 'bg-gradient-to-r from-sky-500 to-blue-600 text-white shadow-sidebar-nav shadow-sky-500/25 scale-[1.01]'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/90'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <div
                    className={`p-1 rounded-lg transition-colors ${
                      isActive ? 'text-white' : 'text-sky-600 bg-sky-50'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                  </div>
                  <span className="truncate">{item.label}</span>
                </div>

                {item.tag && (
                  <span
                    className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full uppercase tracking-wider ${
                      isActive ? 'bg-white/20 text-white' : 'bg-sky-100 text-sky-700'
                    }`}
                  >
                    {item.tag}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Bottom Regional Intelligence Card */}
        <div className="p-4 border-t border-slate-100 bg-slate-50/70">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-teal-400 to-emerald-600 flex items-center justify-center text-white shadow-sm">
              <Compass className="w-4 h-4" />
            </div>
            <div>
              <p className="text-xs font-bold text-slate-900">Uttar Pradesh</p>
              <p className="text-[11px] text-slate-500 font-medium">Environmental Intelligence</p>
            </div>
          </div>
          <div className="mt-2 text-[10px] text-slate-500 bg-white border border-slate-200/80 rounded px-2 py-1 text-center font-mono">
            Pilots: Gorakhpur • Mahoba
          </div>
        </div>
      </aside>
    </>
  );
};
