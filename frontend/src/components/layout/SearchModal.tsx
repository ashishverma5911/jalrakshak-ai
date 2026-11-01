import React, { useState, useEffect } from 'react';
import { Search, X, Droplets, SunMedium, MapPin } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { NavigationRoute, PilotLocationId } from '../../types';

export const SearchModal: React.FC = () => {
  const { isSearchOpen, setIsSearchOpen, setCurrentRoute, setSelectedLocation } = useApp();
  const [query, setQuery] = useState('');

  useEffect(() => {
    if (!isSearchOpen) setQuery('');
  }, [isSearchOpen]);

  if (!isSearchOpen) return null;

  const locations = [
    { id: 'gorakhpur' as PilotLocationId, name: 'Gorakhpur', type: 'flood' as const, sub: 'Rapti Basin • High Flood Sensitivity', route: 'flood' as NavigationRoute },
    { id: 'mahoba' as PilotLocationId, name: 'Mahoba', type: 'drought' as const, sub: 'Bundelkhand • Seasonal Drought Deficit', route: 'drought' as NavigationRoute },
    { id: 'all' as PilotLocationId, name: 'Uttar Pradesh (All Districts)', type: 'overview' as const, sub: 'Statewide Risk Overview', route: 'map' as NavigationRoute },
  ];

  const filteredLocations = locations.filter((loc) =>
    loc.name.toLowerCase().includes(query.toLowerCase()) || loc.sub.toLowerCase().includes(query.toLowerCase())
  );

  const quickPages: { name: string; route: NavigationRoute; sub: string }[] = [
    { name: 'Interactive Risk Map', route: 'map', sub: 'Choropleth district hazard map' },
    { name: 'Rainfall & Historical Trends', route: 'trends', sub: '10-year CHIRPS & GPM rainfall metrics' },
    { name: 'AI Assistant (Gemma 4)', route: 'assistant', sub: 'Data explanations & grounded query reasoning' },
    { name: 'Preparedness & Safety', route: 'preparedness', sub: 'Action checklists & official contacts' },
    { name: 'Data Sources & Methodology', route: 'sources', sub: 'Data provenance, SPI formulas & disclosures' },
    { name: 'System Monitoring', route: 'monitoring', sub: 'API status & data ingestion pipelines' },
  ];

  const filteredPages = quickPages.filter((p) =>
    p.name.toLowerCase().includes(query.toLowerCase()) || p.sub.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-slate-900/40 backdrop-blur-sm animate-fadeIn">
      <div className="w-full max-w-xl bg-white border border-slate-200 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Search Input Bar */}
        <div className="p-4 border-b border-slate-100 flex items-center space-x-3">
          <Search className="w-5 h-5 text-blue-600" />
          <input
            type="text"
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type district or page (e.g. Gorakhpur, Drought, Map)..."
            className="w-full bg-transparent text-slate-900 placeholder-slate-400 text-sm focus:outline-none"
          />
          <button
            onClick={() => setIsSearchOpen(false)}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search Results */}
        <div className="max-h-96 overflow-y-auto p-4 space-y-4">
          <div>
            <h4 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2">
              Pilot Locations
            </h4>
            <div className="space-y-1.5">
              {filteredLocations.map((loc) => (
                <button
                  key={loc.id}
                  onClick={() => {
                    setSelectedLocation(loc.id);
                    setCurrentRoute(loc.route);
                    setIsSearchOpen(false);
                  }}
                  className="w-full p-2.5 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 hover:border-blue-400 flex items-center justify-between text-left group transition-all"
                >
                  <div className="flex items-center space-x-3">
                    <div
                      className={`p-2 rounded-lg ${
                        loc.type === 'flood'
                          ? 'bg-sky-50 text-sky-600'
                          : loc.type === 'drought'
                          ? 'bg-amber-50 text-amber-600'
                          : 'bg-emerald-50 text-emerald-600'
                      }`}
                    >
                      {loc.type === 'flood' ? (
                        <Droplets className="w-4 h-4" />
                      ) : loc.type === 'drought' ? (
                        <SunMedium className="w-4 h-4" />
                      ) : (
                        <MapPin className="w-4 h-4" />
                      )}
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-slate-900 group-hover:text-blue-600">
                        {loc.name}
                      </div>
                      <div className="text-xs text-slate-500">{loc.sub}</div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div>
            <h4 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2">
              Platform Views & Capabilities
            </h4>
            <div className="space-y-1.5">
              {filteredPages.map((page) => (
                <button
                  key={page.route}
                  onClick={() => {
                    setCurrentRoute(page.route);
                    setIsSearchOpen(false);
                  }}
                  className="w-full p-2.5 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 hover:border-blue-400 flex items-center justify-between text-left group transition-all"
                >
                  <div>
                    <div className="text-sm font-semibold text-slate-900 group-hover:text-blue-600">
                      {page.name}
                    </div>
                    <div className="text-xs text-slate-500">{page.sub}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer tip */}
        <div className="p-3 bg-slate-50 border-t border-slate-200 text-[11px] text-slate-500 flex justify-between items-center px-4">
          <span>Tip: Press ESC to close</span>
          <span className="font-mono text-blue-600 font-semibold">JalRakshak Intelligence</span>
        </div>
      </div>
    </div>
  );
};
