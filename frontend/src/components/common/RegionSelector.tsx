import React, { useState, useRef, useEffect } from 'react';
import { MapPin, ChevronDown, Check, Search, AlertCircle, Loader2, ShieldCheck, Database } from 'lucide-react';
import { useApp } from '../../context/AppContext';

export const RegionSelector: React.FC = () => {
  const {
    selectedState,
    setSelectedState,
    selectedLocation,
    setSelectedLocation,
    availableDistricts,
    isLoadingDistricts,
    districtsError,
    activeLocationData,
    isConfiguredPilot,
  } = useApp();

  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const filteredDistricts = availableDistricts.filter((d) => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return true;
    const nameMatch = d.name.toLowerCase().includes(q);
    const hindiMatch = (d.metadata as any)?.hindi_name?.includes(q);
    const codeMatch = d.code.toLowerCase().includes(q);
    return nameMatch || hindiMatch || codeMatch;
  });

  const handleSelectDistrict = (district: any) => {
    const legacyId = district.metadata?.legacy_id || district.id.replace('district-', '');
    setSelectedLocation(legacyId);
    setIsOpen(false);
    setSearchQuery('');
  };

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-navy-850 hover:bg-navy-800 border border-navy-700/80 hover:border-cyan-500/50 text-slate-200 text-xs font-medium shadow-sm transition-all duration-200 interactive-btn"
        aria-haspopup="true"
        aria-expanded={isOpen}
      >
        <MapPin className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
        <span className="font-semibold text-white">
          {selectedState === 'state-uttar-pradesh' ? 'UP' : 'BR'} :
        </span>
        <span className="truncate max-w-[120px] sm:max-w-[160px]">
          {activeLocationData.name}
        </span>
        {isConfiguredPilot ? (
          <span className="hidden sm:inline-flex px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
            Pilot
          </span>
        ) : (
          <span className="hidden sm:inline-flex px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-slate-700/40 text-slate-400 border border-slate-700/60">
            Pending
          </span>
        )}
        <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Cascading Popover */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl bg-navy-900 border border-navy-700 shadow-2xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150">
          {/* Header & Hierarchy Bar */}
          <div className="p-3.5 border-b border-navy-800 bg-navy-950/80">
            <div className="flex items-center justify-between mb-2.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                Administrative Hierarchy
              </span>
              <span className="inline-flex items-center text-[11px] font-semibold text-cyan-400">
                Country: India (IN)
              </span>
            </div>

            {/* State Switcher Tabs */}
            <div className="grid grid-cols-2 gap-1.5 p-1 rounded-xl bg-navy-900 border border-navy-800">
              <button
                type="button"
                onClick={() => setSelectedState('state-uttar-pradesh')}
                className={`py-1.5 text-xs font-semibold rounded-lg transition-all ${
                  selectedState === 'state-uttar-pradesh'
                    ? 'bg-gradient-to-r from-sky-500 to-blue-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white hover:bg-navy-800'
                }`}
              >
                Uttar Pradesh (75)
              </button>
              <button
                type="button"
                onClick={() => setSelectedState('state-bihar')}
                className={`py-1.5 text-xs font-semibold rounded-lg transition-all ${
                  selectedState === 'state-bihar'
                    ? 'bg-gradient-to-r from-sky-500 to-blue-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white hover:bg-navy-800'
                }`}
              >
                Bihar (38)
              </button>
            </div>
          </div>

          {/* Search Box */}
          <div className="p-3 border-b border-navy-800/80 bg-navy-900/60">
            <div className="relative">
              <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={`Search ${selectedState === 'state-uttar-pradesh' ? 'UP' : 'Bihar'} districts...`}
                className="w-full pl-9 pr-3 py-1.5 text-xs rounded-xl bg-navy-850 border border-navy-700 text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                autoFocus
              />
            </div>
          </div>

          {/* District List with Loading & Error States */}
          <div className="max-h-64 overflow-y-auto p-2 space-y-1 divide-y divide-navy-800/40">
            {isLoadingDistricts ? (
              <div className="p-8 text-center text-xs text-slate-400 flex flex-col items-center justify-center space-y-2">
                <Loader2 className="w-5 h-5 text-cyan-400 animate-spin" />
                <span>Loading administrative districts...</span>
              </div>
            ) : districtsError ? (
              <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-xs text-amber-300 flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{districtsError}. Using fallback registry.</span>
              </div>
            ) : filteredDistricts.length === 0 ? (
              <div className="p-6 text-center text-xs text-slate-500">
                No districts matching "{searchQuery}"
              </div>
            ) : (
              filteredDistricts.map((d) => {
                const legacyId = d.metadata?.legacy_id || d.id.replace('district-', '');
                const isSelected = selectedLocation === legacyId || selectedLocation === d.id;
                const isPilot = legacyId === 'gorakhpur' || legacyId === 'mahoba';
                const pilotHazard = legacyId === 'gorakhpur' ? 'Flood Pilot' : (legacyId === 'mahoba' ? 'Drought Pilot' : null);

                return (
                  <button
                    key={d.id}
                    type="button"
                    onClick={() => handleSelectDistrict(d)}
                    className={`w-full flex items-center justify-between px-3 py-2 text-xs rounded-xl transition text-left group ${
                      isSelected
                        ? 'bg-cyan-500/15 text-cyan-200 border border-cyan-500/30'
                        : 'text-slate-300 hover:bg-navy-800 hover:text-white'
                    }`}
                  >
                    <div className="flex flex-col min-w-0 pr-2">
                      <div className="flex items-center space-x-1.5">
                        <span className="font-semibold truncate">{d.name}</span>
                        {(d.metadata as any)?.hindi_name && (
                          <span className="text-[10px] text-slate-500 truncate">
                            • {(d.metadata as any).hindi_name}
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] text-slate-500 font-mono">
                        {d.code} • {(d.metadata as any)?.river_basin || 'Catchment Area'}
                      </span>
                    </div>

                    <div className="flex items-center space-x-2 shrink-0">
                      {isPilot ? (
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                          legacyId === 'gorakhpur'
                            ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40'
                            : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                        }`}>
                          {pilotHazard}
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-800 text-slate-400 border border-slate-700/60">
                          Data Pending
                        </span>
                      )}
                      {isSelected && <Check className="w-3.5 h-3.5 text-cyan-400" />}
                    </div>
                  </button>
                );
              })
            )}
          </div>

          {/* Footer Transparency Disclosure */}
          <div className="p-2.5 border-t border-navy-800 bg-navy-950/90 text-[10px] text-slate-400 flex items-center justify-between">
            <span className="flex items-center space-x-1.5">
              <Database className="w-3 h-3 text-cyan-400" />
              <span>Multi-Region Spatial Hierarchy (113 Districts)</span>
            </span>
            <span className="text-slate-500">EPSG:4326</span>
          </div>
        </div>
      )}
    </div>
  );
};
