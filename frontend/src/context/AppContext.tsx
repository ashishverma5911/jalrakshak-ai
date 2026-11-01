import React, { createContext, useContext, useState, useEffect } from 'react';
import { NavigationRoute, PilotLocationId, PilotLocation, RegionSummary, DataMode } from '../types';
import { apiService } from '../services/api';

export const PILOT_LOCATIONS: Record<string, PilotLocation> = {
  gorakhpur: {
    id: 'gorakhpur',
    name: 'Gorakhpur',
    hindiName: 'गोरखपुर',
    focusType: 'flood',
    coordinates: { lat: 26.7606, lng: 83.3732 },
    region: 'Eastern Terai Plain',
    riverBasin: 'Rapti & Rohini Basin',
    description: 'UPSDMA hyper-sensitive flood district prone to rapid riverine swelling and terrain inundation.',
    isConfiguredPilot: true,
  },
  mahoba: {
    id: 'mahoba',
    name: 'Mahoba',
    hindiName: 'महोबा',
    focusType: 'drought',
    coordinates: { lat: 25.2953, lng: 79.8630 },
    region: 'Bundelkhand Plateau',
    riverBasin: 'Ken & Betwa Interfluve',
    description: 'Drought-vulnerable agro-climatic zone characterized by acute seasonal deficits and rocky aquifers.',
    isConfiguredPilot: true,
  },
  all: {
    id: 'all',
    name: 'Uttar Pradesh (Statewide)',
    hindiName: 'उत्तर प्रदेश',
    focusType: 'overview',
    coordinates: { lat: 26.8467, lng: 80.9462 },
    region: 'Northern India',
    description: 'Statewide environmental intelligence overview across 75 districts.',
    isConfiguredPilot: true,
  },
};

export type DataFreshnessMode = 'fresh' | 'stale' | 'loading' | 'error';

interface AppContextType {
  currentRoute: NavigationRoute;
  setCurrentRoute: (route: NavigationRoute) => void;
  selectedLocation: PilotLocationId;
  setSelectedLocation: (id: PilotLocationId) => void;
  activeLocationData: PilotLocation;
  isConfiguredPilot: boolean;
  selectedState: 'state-uttar-pradesh' | 'state-bihar';
  setSelectedState: (state: 'state-uttar-pradesh' | 'state-bihar') => void;
  availableDistricts: RegionSummary[];
  isLoadingDistricts: boolean;
  districtsError: string | null;
  isSearchOpen: boolean;
  setIsSearchOpen: (open: boolean) => void;
  isNotificationsOpen: boolean;
  setIsNotificationsOpen: (open: boolean) => void;
  isSidebarOpen: boolean;
  setIsSidebarOpen: (open: boolean) => void;
  themeMode: 'overview' | 'flood' | 'drought';
  dataMode: DataMode;
  dataFreshnessMode: DataFreshnessMode;
  setDataFreshnessMode: (mode: DataFreshnessMode) => void;
  activeMapLayer: 'flood' | 'drought' | 'rainfall' | 'elevation';
  setActiveMapLayer: (layer: 'flood' | 'drought' | 'rainfall' | 'elevation') => void;
  checklistState: Record<string, boolean>;
  toggleChecklistItem: (id: string) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentRoute, setCurrentRoute] = useState<NavigationRoute>('dashboard');
  const [selectedLocation, setSelectedLocation] = useState<PilotLocationId>('gorakhpur');
  const [selectedState, setSelectedState] = useState<'state-uttar-pradesh' | 'state-bihar'>('state-uttar-pradesh');
  const [availableDistricts, setAvailableDistricts] = useState<RegionSummary[]>([]);
  const [isLoadingDistricts, setIsLoadingDistricts] = useState<boolean>(false);
  const [districtsError, setDistrictsError] = useState<string | null>(null);

  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [dataFreshnessMode, setDataFreshnessMode] = useState<DataFreshnessMode>('fresh');
  const [activeMapLayer, setActiveMapLayer] = useState<'flood' | 'drought' | 'rainfall' | 'elevation'>('flood');

  // Fetch districts for selected state dynamically
  useEffect(() => {
    setIsLoadingDistricts(true);
    setDistrictsError(null);
    const stateCode = selectedState === 'state-uttar-pradesh' ? 'UP' : 'BR';
    apiService
      .fetchRegions({ region_type: 'district', state: stateCode })
      .then((data) => {
        const list = Array.isArray(data) ? data : (data as any).regions || [];
        setAvailableDistricts(list);
      })
      .catch((err) => {
        setDistrictsError(err?.message || 'Regional hierarchy feed offline');
      })
      .finally(() => {
        setIsLoadingDistricts(false);
      });
  }, [selectedState]);

  // Persistent checklist state
  const [checklistState, setChecklistState] = useState<Record<string, boolean>>(() => {
    try {
      const saved = localStorage.getItem('jalrakshak_checklist');
      return saved ? JSON.parse(saved) : { f1: true, f2: true, d1: true };
    } catch {
      return { f1: true, f2: true, d1: true };
    }
  });

  const toggleChecklistItem = (id: string) => {
    setChecklistState((prev) => {
      const updated = { ...prev, [id]: !prev[id] };
      try {
        localStorage.setItem('jalrakshak_checklist', JSON.stringify(updated));
      } catch {}
      return updated;
    });
  };

  // Determine active pilot status
  const isConfiguredPilot = selectedLocation === 'gorakhpur' || selectedLocation === 'mahoba' || selectedLocation === 'all';
  const dataMode: DataMode = isConfiguredPilot ? 'CACHED_VERIFIED' : 'DATA_PENDING';

  // Resolve active location data dynamically
  const matchingDistrict = availableDistricts.find(
    (d) =>
      d.id === selectedLocation ||
      d.code.toLowerCase() === selectedLocation.toLowerCase() ||
      d.id === `district-${selectedLocation.toLowerCase()}`
  );

  const activeLocationData: PilotLocation = PILOT_LOCATIONS[selectedLocation] || {
    id: selectedLocation,
    name: matchingDistrict?.name || (selectedLocation.charAt(0).toUpperCase() + selectedLocation.slice(1)),
    hindiName: (matchingDistrict?.metadata as any)?.hindi_name || '',
    focusType: 'overview',
    coordinates: {
      lat: (matchingDistrict?.metadata as any)?.lat || (selectedState === 'state-bihar' ? 25.5941 : 26.8467),
      lng: (matchingDistrict?.metadata as any)?.lng || (selectedState === 'state-bihar' ? 85.1376 : 80.9462),
    },
    region: (matchingDistrict?.metadata as any)?.region || (selectedState === 'state-bihar' ? 'Bihar Plain' : 'Uttar Pradesh'),
    riverBasin: (matchingDistrict?.metadata as any)?.river_basin,
    description: 'Candidate administrative district. Observational precipitation ingestion and scientific hazard modeling are currently pending onboarding.',
    isConfiguredPilot: false,
  };

  // Compute theme mode based on active route or current focus
  let themeMode: 'overview' | 'flood' | 'drought' = 'overview';
  if (currentRoute === 'flood') {
    themeMode = 'flood';
  } else if (currentRoute === 'drought') {
    themeMode = 'drought';
  } else if (currentRoute === 'dashboard') {
    if (selectedLocation === 'gorakhpur') themeMode = 'flood';
    else if (selectedLocation === 'mahoba') themeMode = 'drought';
    else themeMode = 'overview';
  }

  // Keyboard shortcut for Cmd/Ctrl+K search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsSearchOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <AppContext.Provider
      value={{
        currentRoute,
        setCurrentRoute,
        selectedLocation,
        setSelectedLocation,
        activeLocationData,
        isConfiguredPilot,
        selectedState,
        setSelectedState,
        availableDistricts,
        isLoadingDistricts,
        districtsError,
        isSearchOpen,
        setIsSearchOpen,
        isNotificationsOpen,
        setIsNotificationsOpen,
        isSidebarOpen,
        setIsSidebarOpen,
        themeMode,
        dataMode,
        dataFreshnessMode,
        setDataFreshnessMode,
        activeMapLayer,
        setActiveMapLayer,
        checklistState,
        toggleChecklistItem,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
