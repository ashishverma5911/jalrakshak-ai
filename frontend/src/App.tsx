import React from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { AppShell } from './components/layout/AppShell';
import { MainDashboardView } from './views/MainDashboardView';
import { FloodAssessmentView } from './views/FloodAssessmentView';
import { DroughtAssessmentView } from './views/DroughtAssessmentView';
import { RiskMapView } from './views/RiskMapView';
import { RainfallTrendsView } from './views/RainfallTrendsView';
import { AIAssistantView } from './views/AIAssistantView';
import { PreparednessView } from './views/PreparednessView';
import { DataSourcesView } from './views/DataSourcesView';
import { SystemMonitoringView } from './views/SystemMonitoringView';

const RouteRenderer: React.FC = () => {
  const { currentRoute } = useApp();

  switch (currentRoute) {
    case 'dashboard':
      return <MainDashboardView />;
    case 'flood':
      return <FloodAssessmentView />;
    case 'drought':
      return <DroughtAssessmentView />;
    case 'map':
      return <RiskMapView />;
    case 'trends':
      return <RainfallTrendsView />;
    case 'assistant':
      return <AIAssistantView />;
    case 'preparedness':
      return <PreparednessView />;
    case 'sources':
      return <DataSourcesView />;
    case 'monitoring':
      return <SystemMonitoringView />;
    default:
      return <MainDashboardView />;
  }
};

export const AppContent: React.FC = () => {
  return (
    <AppShell>
      <RouteRenderer />
    </AppShell>
  );
};

export default function App() {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
}
