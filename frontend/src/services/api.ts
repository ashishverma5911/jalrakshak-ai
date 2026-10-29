/**
 * JalRakshak API Client Service Layer
 * Strongly typed interface matching FastAPI Pydantic v2 schemas.
 */

const API_BASE_URL = (((import.meta as any).env?.VITE_API_BASE_URL as string) || '/api/v1').replace(/\/+$/, '');

export interface SourceMetadata {
  source_id: string;
  source_name: string;
  spatial_resolution: string;
  temporal_resolution: string;
  access_url?: string;
  units: string;
  retrieval_timestamp?: string;
}

export interface RiskIndicator {
  indicator_id: string;
  name: string;
  value: number;
  units: string;
  category: 'observed_measurement' | 'derived_indicator' | 'validated_model' | 'official_alert';
  calculation_window: string;
  reference_baseline: string;
  observation_timestamp: string;
  retrieval_timestamp: string;
  quality_status: 'verified' | 'provisional' | 'stale' | 'missing' | 'simulated_demo';
  methodology_version: string;
  limitations: string;
  is_demo_data: boolean;
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

export interface HazardAssessmentResponse {
  location: LocationReference;
  hazard: 'flood' | 'drought' | 'multi_hazard' | 'rainfall';
  risk_level: 'high' | 'moderate' | 'low' | 'nodata';
  assessment_period: string;
  generated_at: string;
  is_demo_data: boolean;
  disclaimer: string;
  indicators: RiskIndicator[];
  sources: SourceMetadata[];
  scientific_notes: string[];
}

export interface QuickMetricCard {
  title: string;
  location: string;
  value: number;
  units: string;
  delta_percentage: number;
  is_positive_delta: boolean;
  hazard_type: string;
  context_note: string;
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
  is_demo_data: boolean;
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
  anomaly_percentage?: number;
  is_zero_measured?: boolean;
  is_missing?: boolean;
  data_quality?: 'observed' | 'zero_precipitation' | 'missing';
}

export interface RainfallTrendsResponse {
  location_id: string;
  location_name: string;
  aggregation: string;
  time_period: string;
  total_rainfall_mm: number;
  historical_baseline_avg_mm: number;
  wet_days_count: number;
  max_daily_rainfall_mm: number;
  max_daily_date?: string;
  departure_percentage: number;
  data_coverage_pct?: number;
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
  rainfall_anomaly_pct: number;
  spi3: number;
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
  fetchDashboard: (location: string = 'gorakhpur'): Promise<DashboardOverviewResponse> => {
    return apiFetch<DashboardOverviewResponse>(`/dashboard?location=${encodeURIComponent(location)}`);
  },

  fetchFloodRisk: (location: string = 'gorakhpur', days: number = 7): Promise<HazardAssessmentResponse> => {
    return apiFetch<HazardAssessmentResponse>(`/risk/flood?location=${encodeURIComponent(location)}&days=${days}`);
  },

  fetchDroughtRisk: (location: string = 'mahoba'): Promise<HazardAssessmentResponse> => {
    return apiFetch<HazardAssessmentResponse>(`/risk/drought?location=${encodeURIComponent(location)}`);
  },

  fetchRainfallTrends: (location: string = 'gorakhpur', range: string = '30d'): Promise<RainfallTrendsResponse> => {
    return apiFetch<RainfallTrendsResponse>(`/trends/rainfall?location=${encodeURIComponent(location)}&range=${encodeURIComponent(range)}`);
  },

  fetchMapLayers: (hazard: string = 'all'): Promise<MapLayersResponse> => {
    return apiFetch<MapLayersResponse>(`/map/layers?hazard=${encodeURIComponent(hazard)}`);
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
};
