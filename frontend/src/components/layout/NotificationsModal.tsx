import React from 'react';
import { X, AlertTriangle, Flame, Bell, CheckCircle2, ExternalLink } from 'lucide-react';
import { useApp } from '../../context/AppContext';

export const NotificationsModal: React.FC = () => {
  const { isNotificationsOpen, setIsNotificationsOpen, setCurrentRoute, setSelectedLocation } = useApp();

  if (!isNotificationsOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-end p-4 bg-slate-900/40 backdrop-blur-sm animate-fadeIn">
      <div className="w-full max-w-md bg-white border border-slate-200 rounded-2xl shadow-2xl overflow-hidden mt-12 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="p-1.5 rounded-lg bg-rose-50 text-rose-600">
              <Bell className="w-4 h-4" />
            </div>
            <h3 className="font-bold text-slate-900 text-base">Alerts & Real-Time Updates</h3>
          </div>
          <button
            onClick={() => setIsNotificationsOpen(false)}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100"
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
            className="p-3.5 rounded-xl bg-rose-50/70 border border-rose-200/90 hover:border-rose-400 hover:bg-rose-50 transition-all cursor-pointer group shadow-sm"
          >
            <div className="flex items-start space-x-3">
              <div className="w-8 h-8 rounded-lg bg-rose-100 text-rose-600 flex items-center justify-center shrink-0 mt-0.5">
                <AlertTriangle className="w-4 h-4" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-bold text-rose-950 group-hover:text-rose-900">
                    High Rainfall Alert
                  </h4>
                  <span className="text-[10px] font-semibold text-rose-700 bg-rose-100 px-1.5 py-0.5 rounded font-mono">Gorakhpur</span>
                </div>
                <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                  Recent 7-day cumulative rainfall reached 512 mm (+48% vs 10-year normal). Low-lying Rapti basin zones vulnerable.
                </p>
                <div className="mt-2 text-[11px] text-rose-700 flex items-center gap-1 font-semibold group-hover:underline">
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
            className="p-3.5 rounded-xl bg-amber-50/70 border border-amber-200/90 hover:border-amber-400 hover:bg-amber-50 transition-all cursor-pointer group shadow-sm"
          >
            <div className="flex items-start space-x-3">
              <div className="w-8 h-8 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center shrink-0 mt-0.5">
                <Flame className="w-4 h-4" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-bold text-amber-950 group-hover:text-amber-900">
                    Drought Watch
                  </h4>
                  <span className="text-[10px] font-semibold text-amber-800 bg-amber-100 px-1.5 py-0.5 rounded font-mono">Mahoba</span>
                </div>
                <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                  90-day rainfall is 62 mm (-58% anomaly; seasonal deficit -72%). Extended dry spells reported in Bundelkhand plateau.
                </p>
                <div className="mt-2 text-[11px] text-amber-800 flex items-center gap-1 font-semibold group-hover:underline">
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
            className="p-3.5 rounded-xl bg-emerald-50/70 border border-emerald-200/90 hover:border-emerald-400 hover:bg-emerald-50 transition-all cursor-pointer group shadow-sm"
          >
            <div className="flex items-start space-x-3">
              <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0 mt-0.5">
                <CheckCircle2 className="w-4 h-4" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-bold text-emerald-950">Data Pipeline Refreshed</h4>
                  <span className="text-[10px] text-emerald-700 font-mono font-semibold">10:30 AM</span>
                </div>
                <p className="text-xs text-slate-600 mt-1">
                  NASA GPM IMERG 0.1° gridded run processed with zero anomalies.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 bg-slate-50 border-t border-slate-200 text-[11px] text-slate-500 flex justify-between items-center px-4">
          <span>Official warnings: UPSDMA / IMD</span>
          <button
            onClick={() => {
              setCurrentRoute('preparedness');
              setIsNotificationsOpen(false);
            }}
            className="text-blue-600 hover:text-blue-800 font-medium hover:underline"
          >
            Safety Guidelines
          </button>
        </div>
      </div>
    </div>
  );
};
