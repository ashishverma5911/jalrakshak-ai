import React from 'react';
import { X, AlertTriangle, Flame, Bell, CheckCircle2, ExternalLink } from 'lucide-react';
import { useApp } from '../../context/AppContext';

export const NotificationsModal: React.FC = () => {
  const { isNotificationsOpen, setIsNotificationsOpen, setCurrentRoute, setSelectedLocation } = useApp();

  if (!isNotificationsOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-end p-4 bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-md bg-navy-900 border border-navy-700 rounded-2xl shadow-2xl overflow-hidden mt-12 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-navy-800 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <Bell className="w-5 h-5 text-rose-400" />
            <h3 className="font-bold text-white text-base">Alerts & Real-Time Updates</h3>
          </div>
          <button
            onClick={() => setIsNotificationsOpen(false)}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-navy-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* List of Alerts */}
        <div className="p-4 space-y-3 max-h-[70vh] overflow-y-auto">
          {/* Gorakhpur High Rainfall Alert */}
          <div
            onClick={() => {
              setSelectedLocation('gorakhpur');
              setCurrentRoute('flood');
              setIsNotificationsOpen(false);
            }}
            className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 hover:border-rose-500/60 transition-all cursor-pointer group"
          >
            <div className="flex items-start space-x-3">
              <div className="w-8 h-8 rounded-lg bg-rose-500/20 text-rose-400 flex items-center justify-center shrink-0 mt-0.5">
                <AlertTriangle className="w-4 h-4" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-semibold text-rose-200 group-hover:text-rose-100">
                    High Rainfall Alert
                  </h4>
                  <span className="text-[10px] text-rose-300 font-mono">Gorakhpur</span>
                </div>
                <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                  Recent 7-day cumulative rainfall reached 512 mm (+48% vs 10-year normal). Low-lying Rapti basin zones vulnerable.
                </p>
                <div className="mt-2 text-[11px] text-rose-400 flex items-center gap-1 font-medium">
                  <span>Inspect flood assessment</span>
                  <ExternalLink className="w-3 h-3" />
                </div>
              </div>
            </div>
          </div>

          {/* Mahoba Drought Watch */}
          <div
            onClick={() => {
              setSelectedLocation('mahoba');
              setCurrentRoute('drought');
              setIsNotificationsOpen(false);
            }}
            className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 hover:border-amber-500/60 transition-all cursor-pointer group"
          >
            <div className="flex items-start space-x-3">
              <div className="w-8 h-8 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center shrink-0 mt-0.5">
                <Flame className="w-4 h-4" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-semibold text-amber-200 group-hover:text-amber-100">
                    Drought Watch
                  </h4>
                  <span className="text-[10px] text-amber-300 font-mono">Mahoba</span>
                </div>
                <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                  90-day rainfall is 62 mm (-58% anomaly; seasonal deficit -72%). Extended dry spells reported in Bundelkhand plateau.
                </p>
                <div className="mt-2 text-[11px] text-amber-400 flex items-center gap-1 font-medium">
                  <span>Inspect drought assessment</span>
                  <ExternalLink className="w-3 h-3" />
                </div>
              </div>
            </div>
          </div>

          {/* Pipeline Success */}
          <div
            onClick={() => {
              setCurrentRoute('monitoring');
              setIsNotificationsOpen(false);
            }}
            className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 hover:border-emerald-500/40 transition-all cursor-pointer group"
          >
            <div className="flex items-start space-x-3">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0 mt-0.5">
                <CheckCircle2 className="w-4 h-4" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-semibold text-emerald-200">Data Pipeline Refreshed</h4>
                  <span className="text-[10px] text-emerald-400 font-mono">10:30 AM</span>
                </div>
                <p className="text-xs text-slate-300 mt-1">
                  NASA GPM IMERG 0.1° gridded run processed with zero anomalies.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 bg-navy-950 border-t border-navy-800 text-[11px] text-slate-400 flex justify-between items-center px-4">
          <span>Official warnings: UPSDMA / IMD</span>
          <button
            onClick={() => {
              setCurrentRoute('preparedness');
              setIsNotificationsOpen(false);
            }}
            className="text-cyan-400 hover:underline"
          >
            Safety Guidelines
          </button>
        </div>
      </div>
    </div>
  );
};
