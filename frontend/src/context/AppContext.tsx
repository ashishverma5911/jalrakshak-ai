import React, { createContext, useContext, useState, useEffect } from 'react';
import { NavigationRoute, PilotLocationId, PilotLocation } from '../types';

export const PILOT_LOCATIONS: Record<PilotLocationId, PilotLocation> = {
  gorakhpur: {
    id: 'gorakhpur',
    name: 'Gorakhpur',
    hindiName: 'गोरखपुर',
    focusType: 'flood',
    coordinates: { lat: 26.7606, lng: 83.3732 },
    region: 'Eastern Terai Plain',
    riverBasin: 'Rapti & Rohini Basin',
    description: 'UPSDMA hyper-sensitive flood district prone to rapid riverine swelling and terrain inundation.',
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
  },
  all: {
    id: 'all',
    name: 'Uttar Pradesh (Statewide)',
    hindiName: 'उत्तर प्रदेश',
    focusType: 'overview',
    coordinates: { lat: 26.8467, lng: 80.9462 },
    region: 'Northern India',
    description: 'Statewide environmental intelligence overview across 75 districts.',
  },
};

export type DataFreshnessMode = 'fresh' | 'stale' | 'loading' | 'error';

interface AppContextType {
  currentRoute: NavigationRoute;
  setCurrentRoute: (route: NavigationRoute) => void;
  selectedLocation: PilotLocationId;
  setSelectedLocation: (id: PilotLocationId) => void;
  activeLocationData: PilotLocation;
  isSearchOpen: boolean;
  setIsSearchOpen: (open: boolean) => void;
  isNotificationsOpen: boolean;
  setIsNotificationsOpen: (open: boolean) => void;
  isSidebarOpen: boolean;
  setIsSidebarOpen: (open: boolean) => void;
  themeMode: 'overview' | 'flood' | 'drought';
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
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [dataFreshnessMode, setDataFreshnessMode] = useState<DataFreshnessMode>('fresh');
  const [activeMapLayer, setActiveMapLayer] = useState<'flood' | 'drought' | 'rainfall' | 'elevation'>('flood');

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
        activeLocationData: PILOT_LOCATIONS[selectedLocation],
        isSearchOpen,
        setIsSearchOpen,
        isNotificationsOpen,
        setIsNotificationsOpen,
        isSidebarOpen,
        setIsSidebarOpen,
        themeMode,
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
