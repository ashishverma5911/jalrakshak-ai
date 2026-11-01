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

export type PilotLocationId = 'gorakhpur' | 'mahoba' | 'all' | string;

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
  isConfiguredPilot?: boolean;
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

export interface HazardSummary {
  code: string;
  name?: string;
  status: string;
  is_enabled: boolean;
  configuration?: Record<string, any>;
}

export interface RegionSummary {
  id: string;
  code: string;
  name: string;
  region_type: 'country' | 'state' | 'district' | 'subdistrict' | string;
  parent_id?: string | null;
  country_code: string;
  state_code?: string | null;
  is_active: boolean;
  supported_hazards: HazardSummary[];
  metadata?: Record<string, any>;
}

export interface RegionDetail extends RegionSummary {
  created_at?: string | null;
  updated_at?: string | null;
}

export interface RegionHazardItem {
  id: string;
  region_id: string;
  hazard_type_id: string;
  hazard_code: string;
  hazard_name: string;
  is_enabled: boolean;
  configuration: Record<string, any>;
}

export interface RegionHazardsResponse {
  region_id: string;
  region_code: string;
  region_name: string;
  hazards: RegionHazardItem[];
}

export type RegionListResponse = RegionSummary[];

export type DataMode =
  | 'LIVE_VERIFIED'
  | 'CACHED_VERIFIED'
  | 'DEMONSTRATION'
  | 'DATA_PENDING'
  | 'DATA_STALE'
  | 'MANUAL_UPLOAD';

export type DataClassification =
  | 'IN_SITU_GROUND_TRUTH'
  | 'SATELLITE_DERIVED_OR_BLENDED'
  | 'MODELLED_OR_REANALYSIS'
  | 'MANUAL_UPLOAD'
  | 'DEMONSTRATION';

export type ProcessingStage =
  | 'DATA_PENDING'
  | 'QUARANTINED'
  | 'VALIDATING'
  | 'STRUCTURE_VALIDATED'
  | 'SCIENTIFICALLY_DECODED'
  | 'SPATIALLY_VALIDATED'
  | 'VERIFIED_REAL'
  | 'DEMONSTRATION'
  | 'REJECTED'
  | 'UNSUPPORTED'
  | 'DATA_UNAVAILABLE';
