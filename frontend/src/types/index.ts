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
  | 'LIVE_MODEL'
  | 'PROVIDER_ERROR'
  | 'MANUAL_UPLOAD'
  | 'FORECAST'
  | 'CACHED';

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

export interface HourlyEnvironmentalPoint {
  timestamp: string;
  precipitation_mm: number | null;
  temperature_2m_c: number | null;
  relative_humidity_pct: number | null;
  wind_speed_10m_kmh: number | null;
  et0_evapotranspiration_mm: number | null;
  is_forecast: boolean;
  quality_status: string;
}

export interface DailyAggregatedPrecipitation {
  date: string;
  rainfall_mm: number | null;
  is_forecast: boolean;
  hours_recorded: number;
  hours_missing: number;
  quality_status: string;
}

export interface CurrentEnvironmentalConditions {
  timestamp: string;
  temperature_2m_c?: number | null;
  relative_humidity_pct?: number | null;
  wind_speed_10m_kmh?: number | null;
  precipitation_rate_mm_hr?: number | null;
  et0_evapotranspiration_mm?: number | null;
  is_forecast?: boolean;
  condition_summary?: string | null;
}

export interface EnvironmentalDataFreshness {
  latest_timestamp: string;
  retrieval_timestamp: string;
  data_age_hours: number;
  cache_ttl_hours: number;
  is_cached: boolean;
  is_stale: boolean;
  cache_expires_at?: string | null;
}

export interface EnvironmentalLiveResponse {
  district_id: string;
  district_name: string;
  coordinates: {
    lat: number;
    lng: number;
  };
  spatial_representation: string;
  spatial_disclaimer: string;
  provider: string;
  model_name: string;
  attribution: string;
  access_url: string;
  data_mode: DataMode | string;
  freshness: EnvironmentalDataFreshness;
  current_conditions?: CurrentEnvironmentalConditions | null;
  hourly_series: HourlyEnvironmentalPoint[];
  daily_precipitation: DailyAggregatedPrecipitation[];
  provider_status?: Record<string, any> | null;
  scientific_notes: string[];
}

export interface EnvironmentalRefreshResponse {
  success: boolean;
  district_id: string;
  status: string;
  message: string;
  refreshed_at: string;
  cache_expires_at: string;
  data_mode: string;
  data?: EnvironmentalLiveResponse;
}

export interface EnvironmentalSystemStatusResponse {
  feature_flag_enabled: boolean;
  provider: string;
  endpoint: string;
  cache_ttl_hours: number;
  stale_threshold_hours: number;
  timeout_seconds: number;
  max_retries: number;
  active_cached_districts: string[];
  provider_connection_status: string;
  provider_cooldown_active?: boolean;
  cooldown_remaining_seconds?: number;
  provider_cooldown_reason?: string | null;
}
