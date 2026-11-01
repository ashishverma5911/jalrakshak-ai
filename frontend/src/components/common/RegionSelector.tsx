import React, { useState, useRef, useEffect } from 'react';
import { MapPin, ChevronDown, Check, Search, AlertCircle, Loader2, Database } from 'lucide-react';
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
        className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 text-xs font-medium shadow-xs transition-all duration-150 interactive-btn"
        aria-haspopup="true"
        aria-expanded={isOpen}
      >
        <MapPin className="w-3.5 h-3.5 text-blue-600 shrink-0" />
        <span className="font-semibold text-slate-900">
          {(isConfiguredPilot ? 'UP' : selectedState === 'state-uttar-pradesh' ? 'UP' : 'BR')} :
        </span>
        <span className="truncate max-w-[120px] sm:max-w-[160px] text-slate-800">
          {activeLocationData.name}
        </span>
        {isConfiguredPilot ? (
          <span className="hidden sm:inline-flex px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-sky-50 text-sky-700 border border-sky-200">
            Pilot
          </span>
        ) : (
          <span className="hidden sm:inline-flex px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-slate-100 text-slate-600 border border-slate-200">
            Pending
          </span>
        )}
        <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Cascading Popover */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl bg-white border border-slate-200 shadow-2xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150">
          {/* Header & Hierarchy Bar */}
          <div className="p-3.5 border-b border-slate-100 bg-slate-50/70">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                Administrative Hierarchy
              </span>
              <span className="inline-flex items-center text-[11px] font-semibold text-blue-600">
                Country: India (IN)
              </span>
            </div>

            {/* State Switcher Tabs */}
            <div className="grid grid-cols-2 gap-1.5 p-1 rounded-xl bg-slate-100 border border-slate-200">
              <button
                type="button"
                onClick={() => setSelectedState('state-uttar-pradesh')}
                className={`py-1.5 text-xs font-semibold rounded-lg transition-all ${
                  selectedState === 'state-uttar-pradesh'
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                }`}
              >
                Uttar Pradesh (75)
              </button>
              <button
                type="button"
                onClick={() => setSelectedState('state-bihar')}
                className={`py-1.5 text-xs font-semibold rounded-lg transition-all ${
                  selectedState === 'state-bihar'
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                }`}
              >
                Bihar (38)
              </button>
            </div>
          </div>

          {/* Search Box */}
          <div className="p-3 border-b border-slate-100 bg-white">
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={`Search ${selectedState === 'state-uttar-pradesh' ? 'UP' : 'Bihar'} districts...`}
                className="w-full pl-9 pr-3 py-1.5 text-xs rounded-xl bg-slate-50 border border-slate-200 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white"
                autoFocus
              />
            </div>
          </div>

          {/* District List with Loading & Error States */}
          <div className="max-h-64 overflow-y-auto p-2 space-y-1 divide-y divide-slate-100">
            {isLoadingDistricts ? (
              <div className="p-8 text-center text-xs text-slate-500 flex flex-col items-center justify-center space-y-2">
                <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
                <span>Loading administrative districts...</span>
              </div>
            ) : districtsError ? (
              <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-800 flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
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
                        ? 'bg-blue-50 text-blue-900 border border-blue-200 font-medium'
                        : 'text-slate-700 hover:bg-slate-50 hover:text-slate-900'
                    }`}
                  >
                    <div className="flex flex-col min-w-0 pr-2">
                      <div className="flex items-center space-x-1.5">
                        <span className="font-semibold text-slate-900 truncate">{d.name}</span>
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
                            ? 'bg-sky-50 text-sky-700 border border-sky-200'
                            : 'bg-amber-50 text-amber-800 border border-amber-200'
                        }`}>
                          {pilotHazard}
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-100 text-slate-600 border border-slate-200">
                          Data Pending
                        </span>
                      )}
                      {isSelected && <Check className="w-3.5 h-3.5 text-blue-600" />}
                    </div>
                  </button>
                );
              })
            )}
          </div>

          {/* Footer Transparency Disclosure */}
          <div className="p-2.5 border-t border-slate-100 bg-slate-50/90 text-[10px] text-slate-500 flex items-center justify-between">
            <span className="flex items-center space-x-1.5">
              <Database className="w-3 h-3 text-blue-600" />
              <span>Multi-Region Spatial Hierarchy (113 Districts)</span>
            </span>
            <span className="text-slate-400 font-mono">EPSG:4326</span>
          </div>
        </div>
      )}
    </div>
  );
};
