/**
 * JalRakshak API Client Service Layer
 * Strongly typed interface matching FastAPI Pydantic v2 schemas.
 */

import type {
  RegionSummary,
  RegionDetail,
  RegionHazardsResponse,
  RegionListResponse,
  EnvironmentalLiveResponse,
  EnvironmentalRefreshResponse,
  EnvironmentalSystemStatusResponse,
} from '../types';

export type {
  RegionSummary,
  RegionDetail,
  RegionHazardsResponse,
  RegionListResponse,
  EnvironmentalLiveResponse,
  EnvironmentalRefreshResponse,
  EnvironmentalSystemStatusResponse,
};

const API_BASE_URL = (((import.meta as any).env?.VITE_API_BASE_URL as string) || '/api/v1').replace(/\/+$/, '');

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
  | 'HISTORICAL_MODEL_ESTIMATE'
  | 'LIVE_MODEL_ESTIMATE'
  | 'MIXED_MODEL_ESTIMATE'
  | 'MODEL_DERIVED'
  | 'CACHED';

export interface SourceMetadata {
  source_id: string;
  source_name: string;
  spatial_resolution: string;
  temporal_resolution: string;
  dataset_version?: string;
  access_url?: string;
  units: string;
  data_mode?: DataMode;
  retrieval_timestamp?: string;
  license?: string;
}

export interface RiskIndicator {
  indicator_id: string;
  name: string;
  value: number | null;
  units: string;
  category: 'observed_measurement' | 'derived_indicator' | 'validated_model' | 'official_alert' | 'model_derived';
  calculation_window: string;
  reference_baseline: string;
  observation_timestamp: string;
  retrieval_timestamp: string;
  quality_status:
    | 'verified'
    | 'provisional'
    | 'stale'
    | 'missing'
    | 'simulated_demo'
    | 'forecast'
    | 'observed_estimate'
    | 'historical_model_estimate'
    | 'live_model_estimate'
    | 'mixed_model_estimate';
  data_mode?: DataMode;
  dataset_version?: string;
  spatial_resolution?: string;
  methodology_version: string;
  limitations: string;
  is_demo_data: boolean;
  is_data_available?: boolean;
}

export interface LocationReference {
  location_id: string;
  name: string;
  hindi_name: string;
  latitude: number;
  longitude: number;
  elevation_m: number;
  river_basin: string;
  region: string;
  is_pilot: boolean;
}

export type DataCompleteness = 'complete' | 'partial' | 'pending';

export interface OfficialAdvisoryReference {
  authority: string;
  bulletin_id?: string | null;
  alert_level: string;
  is_valid: boolean;
  is_currently_active?: boolean;
  valid_from?: string | null;
  valid_to?: string | null;
  advisory_text?: string | null;
  status?: string | null;
  verification_status?: string | null;
}

export interface HazardAssessmentResponse {
  location: LocationReference;
  hazard: 'flood' | 'drought' | 'multi_hazard' | 'rainfall';
  risk_level: 'high' | 'moderate' | 'low' | 'nodata' | 'pending';
  assessment_period: string;
  generated_at: string;
  assessment_timestamp?: string | null;
  is_historical_replay?: boolean;
  data_mode?: DataMode;
  is_demo_data: boolean;
  is_data_available?: boolean;
  disclaimer: string;
  indicators: RiskIndicator[];
  sources: SourceMetadata[];
  scientific_notes: string[];
  primary_risk_driver?: string | null;
  data_completeness?: DataCompleteness;
  official_advisory?: OfficialAdvisoryReference | null;
}

export interface QuickMetricCard {
  title: string;
  location: string;
  value: number | null;
  units: string;
  delta_percentage?: number | null;
  is_positive_delta?: boolean | null;
  hazard_type: string;
  context_note: string;
  is_data_available?: boolean;
}

export interface AlertNotice {
  id: string;
  title: string;
  location: string;
  severity: string;
  description: string;
  issued_at: string;
  is_official_warning: boolean;
  source_agency: string;
}

export interface DashboardOverviewResponse {
  title: string;
  timestamp: string;
  data_freshness_status: string;
  data_mode?: DataMode;
  is_demo_data: boolean;
  is_data_available?: boolean;
  disclaimer: string;
  pilot_locations: LocationReference[];
  metric_cards: QuickMetricCard[];
  recent_alerts: AlertNotice[];
  active_sources: SourceMetadata[];
}

export interface RainfallSeriesPoint {
  date: string;
  observed_rainfall_mm: number | null;
  historical_avg_mm: number;
  anomaly_percentage?: number | null;
  is_zero_measured?: boolean;
  is_missing?: boolean;
  data_quality?: 'observed' | 'zero_precipitation' | 'missing';
}

export interface RainfallTrendsResponse {
  location_id: string;
  location_name: string;
  aggregation: string;
  time_period: string;
  total_rainfall_mm?: number | null;
  historical_baseline_avg_mm?: number | null;
  wet_days_count?: number | null;
  max_daily_rainfall_mm?: number | null;
  max_daily_date?: string;
  departure_percentage?: number | null;
  data_coverage_pct?: number;
  is_data_available?: boolean;
  data_mode?: DataMode;
  observation_window?: string;
  disclaimer?: string;
  is_demo_data: boolean;
  sources: string[];
  series: RainfallSeriesPoint[];
}

export interface DistrictMapFeature {
  district_id: string;
  name: string;
  hindi_name: string;
  latitude: number;
  longitude: number;
  elevation_m: number;
  river_basin: string;
  is_pilot: boolean;
  flood_risk: string;
  drought_risk: string;
  rainfall_anomaly_pct?: number | null;
  spi3?: number | null;
  is_data_available?: boolean;
  observation_window?: string;
  source_timestamp?: string;
  data_quality?: string;
  geometry_type?: string;
  geometry_available?: boolean;
  last_updated: string;
}

export interface MapLayersResponse {
  layer_type: string;
  generated_at: string;
  is_demo_data: boolean;
  data_mode?: DataMode;
  geometry_status?: string;
  geometry_available?: boolean;
  geometry_disclaimer?: string;
  districts: DistrictMapFeature[];
  metadata: Record<string, any>;
}

export interface HealthResponse {
  status: string;
  api_status?: string;
  project: string;
  version: string;
  timestamp?: string;
  uptime_seconds: number;
  data_staleness_hours?: number;
  stale_detected?: boolean;
  ingestion_status?: string;
  system_time?: string;
  data_ingestion?: {
    status: string;
    active_pipelines: number;
    last_ingestion: string;
    pipeline_mode: string;
  };
  data_freshness?: {
    last_observation_timestamp: string;
    staleness_threshold_hours: number;
    data_age_hours: number;
    is_stale: boolean;
    source_type: string;
  };
  model_runtime?: {
    configured_model: string;
    runtime_adapter: string;
    endpoint_configured: string;
    fallback_engine: string;
    runtime_disclaimer: string;
  };
  is_demo_data: boolean;
  disclaimer?: string;
}

export interface GroundedEvidenceItem {
  indicator_id: string;
  name: string;
  value: number;
  units: string;
  category: string;
  observation_period: string;
  quality_status: string;
}

export interface AssistantChatResponse {
  answer: string;
  runtime_status: 'available' | 'unavailable' | 'offline_demo';
  model_name: string;
  evidence_used: GroundedEvidenceItem[];
  citations: string[];
  relevant_indicators: Record<string, any>[];
  data_timestamps: Record<string, string>;
  is_demo_data: boolean;
  limitations: string[];
  disclaimer: string;
}

export interface ValidationReport {
  is_valid: boolean;
  file_type: string;
  mime_detected: string;
  file_size_bytes: number;
  sha256_hash: string;
  target_region_id?: string;
  data_mode: string;
  data_classification?: string;
  processing_stage?: string;
  scientific_decoding_status?: string;
  spatial_validation_status?: string;
  spatial_overlap_pct?: number;
  spatial_crs?: string;
  spatial_coverage_status?: string;
  bounding_box?: { min_lng: number; min_lat: number; max_lng: number; max_lat: number };
  raster_dimensions?: { width: number; height: number; bands: number };
  temporal_semantics?: string;
  uncompressed_bytes?: number;
  compression_ratio?: number;
  total_records: number;
  valid_records: number;
  missing_records: number;
  extreme_records: number;
  date_range?: { start: string; end: string };
  mean_value?: number;
  max_value?: number;
  min_value?: number;
  warnings: string[];
  errors: string[];
  metadata: Record<string, any>;
}

export interface DatasetUploadResponse {
  upload_id: string;
  filename: string;
  status: 'VALIDATED' | 'REJECTED' | 'INGESTED' | 'UNSUPPORTED' | 'QUARANTINED';
  processing_stage?: string;
  data_classification?: string;
  message: string;
  validation_report: ValidationReport;
  uploaded_at: string;
}

export interface UploadHistoryItem {
  upload_id: string;
  filename: string;
  file_type: string;
  target_region_id?: string;
  records_count: number;
  status: string;
  processing_stage?: string;
  data_classification?: string;
  spatial_overlap_pct?: number;
  file_size_bytes: number;
  uploaded_at: string;
}

/**
 * Universal JSON fetch helper with timeout and typed error reporting
 */
async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 8000);

  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    });

    if (!res.ok) {
      let errMsg = `API error ${res.status}: ${res.statusText}`;
      try {
        const errJson = await res.json();
        if (errJson.detail) {
          errMsg = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
        } else if (errJson.message) {
          errMsg = typeof errJson.message === 'string' ? errJson.message : JSON.stringify(errJson.message);
        }
      } catch {}
      throw new Error(errMsg);
    }

    return (await res.json()) as T;
  } catch (err: any) {
    if (err?.name === 'AbortError') {
      throw new Error(`Request timed out connecting to ${endpoint}.`);
    }
    if (err instanceof TypeError && err.message?.toLowerCase().includes('fetch')) {
      throw new Error(`Network error connecting to FastAPI backend (${url}). Check if server is running.`);
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}

export const apiService = {
  fetchDashboard: (location: string = 'gorakhpur', mode: string = 'verified'): Promise<DashboardOverviewResponse> => {
    return apiFetch<DashboardOverviewResponse>(`/dashboard?location=${encodeURIComponent(location)}&mode=${encodeURIComponent(mode)}`);
  },

  fetchFloodRisk: (location: string = 'gorakhpur', days: number = 7, mode: string = 'verified'): Promise<HazardAssessmentResponse> => {
    return apiFetch<HazardAssessmentResponse>(`/risk/flood?location=${encodeURIComponent(location)}&days=${days}&mode=${encodeURIComponent(mode)}`);
  },

  fetchDroughtRisk: (location: string = 'mahoba', mode: string = 'verified'): Promise<HazardAssessmentResponse> => {
    return apiFetch<HazardAssessmentResponse>(`/risk/drought?location=${encodeURIComponent(location)}&mode=${encodeURIComponent(mode)}`);
  },

  fetchRainfallTrends: (location: string = 'gorakhpur', range: string = '30d', mode: string = 'verified'): Promise<RainfallTrendsResponse> => {
    return apiFetch<RainfallTrendsResponse>(`/trends/rainfall?location=${encodeURIComponent(location)}&range=${encodeURIComponent(range)}&mode=${encodeURIComponent(mode)}`);
  },

  fetchMapLayers: (hazard: string = 'all', mode: string = 'verified'): Promise<MapLayersResponse> => {
    return apiFetch<MapLayersResponse>(`/map/layers?layer=${encodeURIComponent(hazard)}&mode=${encodeURIComponent(mode)}`);
  },

  fetchSources: (): Promise<SourceMetadata[]> => {
    return apiFetch<SourceMetadata[]>('/sources');
  },

  fetchHealth: (): Promise<HealthResponse> => {
    return apiFetch<HealthResponse>('/health');
  },

  sendAssistantChat: (query: string, location: string = 'gorakhpur'): Promise<AssistantChatResponse> => {
    return apiFetch<AssistantChatResponse>('/assistant/chat', {
      method: 'POST',
      body: JSON.stringify({ query, location }),
    });
  },

  fetchRegions: (params?: {
    region_type?: string;
    parent_id?: string;
    state?: string;
    hazard_type?: string;
    is_active?: boolean;
  }): Promise<RegionListResponse> => {
    const query = new URLSearchParams();
    if (params) {
      if (params.region_type) query.set('region_type', params.region_type);
      if (params.parent_id) query.set('parent_id', params.parent_id);
      if (params.state) query.set('state', params.state);
      if (params.hazard_type) query.set('hazard_type', params.hazard_type);
      if (params.is_active !== undefined) query.set('is_active', String(params.is_active));
    }
    const qs = query.toString();
    return apiFetch<RegionListResponse>(`/regions${qs ? `?${qs}` : ''}`);
  },

  fetchRegionById: (regionId: string): Promise<RegionDetail> => {
    return apiFetch<RegionDetail>(`/regions/${encodeURIComponent(regionId)}`);
  },

  fetchRegionHazards: (regionId: string): Promise<RegionHazardsResponse> => {
    return apiFetch<RegionHazardsResponse>(`/regions/${encodeURIComponent(regionId)}/hazards`);
  },

  fetchRegionChildren: (regionId: string): Promise<RegionListResponse> => {
    return apiFetch<RegionListResponse>(`/regions/${encodeURIComponent(regionId)}/children`);
  },

  uploadScientificDataset: async (file: File, targetRegionId?: string): Promise<DatasetUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    if (targetRegionId) {
      formData.append('target_region_id', targetRegionId);
    }
    const res = await fetch(`${API_BASE_URL}/uploads/scientific-dataset`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Dataset upload failed.');
    }
    return res.json();
  },

  fetchUploadHistory: (): Promise<UploadHistoryItem[]> => {
    return apiFetch<UploadHistoryItem[]>('/uploads/history');
  },

  cleanupQuarantine: (maxAgeHours: number = 24.0): Promise<{ deleted_files_count: number; reclaimed_bytes: number; current_storage_bytes: number }> => {
    return apiFetch<{ deleted_files_count: number; reclaimed_bytes: number; current_storage_bytes: number }>(
      `/uploads/cleanup?max_age_hours=${maxAgeHours}`,
      { method: 'POST' }
    );
  },

  fetchEnvironmentalLive: (location: string = 'gorakhpur', refresh: boolean = false): Promise<EnvironmentalLiveResponse> => {
    return apiFetch<EnvironmentalLiveResponse>(`/environmental/live?location=${encodeURIComponent(location)}&refresh=${refresh}`);
  },

  fetchEnvironmentalStatus: (): Promise<EnvironmentalSystemStatusResponse> => {
    return apiFetch<EnvironmentalSystemStatusResponse>('/environmental/status');
  },

  refreshEnvironmentalData: (location: string = 'gorakhpur'): Promise<EnvironmentalRefreshResponse> => {
    return apiFetch<EnvironmentalRefreshResponse>(`/environmental/refresh?location=${encodeURIComponent(location)}`, {
      method: 'POST',
    });
  },
};
