export type NavigationRoute =
  | 'dashboard'
  | 'flood'
  | 'drought'
  | 'map'
  | 'trends'
  | 'assistant'
  | 'preparedness'
  | 'sources'
  | 'monitoring';

export type PilotLocationId = 'gorakhpur' | 'mahoba' | 'all';

export interface PilotLocation {
  id: PilotLocationId;
  name: string;
  hindiName: string;
  focusType: 'flood' | 'drought' | 'overview';
  coordinates: {
    lat: number;
    lng: number;
  };
  region: string;
  riverBasin?: string;
  description: string;
}

export type RiskLevel = 'high' | 'moderate' | 'low' | 'nodata';

export interface QuickStat {
  title: string;
  location: string;
  value: string;
  delta: string;
  isPositiveDelta?: boolean;
  type: 'flood' | 'drought';
}

export interface SystemHealthStatus {
  apiStatus: 'online' | 'degraded' | 'offline';
  dataIngestion: 'running' | 'idle' | 'failed';
  lastUpdate: string;
  uptime24h: number;
  activeModel: string;
}
