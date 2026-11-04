import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import App from '../App';
import { apiService, DashboardOverviewResponse } from '../services/api';

const MOCK_VERIFIED_DASHBOARD: DashboardOverviewResponse = {
  title: 'JalRakshak Environmental Intelligence',
  timestamp: '2026-11-04T13:45:53.318144+00:00',
  data_freshness_status: 'verified',
  data_mode: 'CACHED_VERIFIED',
  is_demo_data: false,
  is_data_available: true,
  disclaimer:
    'JalRakshak AI Decision-Support System. Grounded in validated CHIRPS v2.0 & NASA GPM observational baselines. Not an official statutory forecasting authority.',
  pilot_locations: [
    {
      location_id: 'gorakhpur',
      name: 'Gorakhpur',
      hindi_name: 'गोरखपुर',
      latitude: 26.7606,
      longitude: 83.3732,
      elevation_m: 84.0,
      river_basin: 'Rapti & Rohini Basin',
      region: 'Eastern Terai Plain',
      is_pilot: true,
    },
    {
      location_id: 'mahoba',
      name: 'Mahoba',
      hindi_name: 'महोबा',
      latitude: 25.2953,
      longitude: 79.863,
      elevation_m: 214.0,
      river_basin: 'Ken & Betwa Interfluve',
      region: 'Bundelkhand Plateau',
      is_pilot: true,
    },
  ],
  metric_cards: [
    {
      title: 'Current Rainfall',
      location: 'Gorakhpur',
      value: 0.0,
      units: 'mm',
      delta_percentage: -100.0,
      is_positive_delta: false,
      hazard_type: 'flood',
      context_note: '7-day cumulative rainfall volume',
      is_data_available: true,
    },
    {
      title: '30-Day Cumulative',
      location: 'Gorakhpur',
      value: 16.8,
      units: 'mm',
      delta_percentage: -58.2,
      is_positive_delta: false,
      hazard_type: 'flood',
      context_note: '30-day cumulative precipitation volume',
      is_data_available: true,
    },
    {
      title: '90-Day Rainfall',
      location: 'Mahoba',
      value: 719.7,
      units: 'mm',
      delta_percentage: 58.7,
      is_positive_delta: true,
      hazard_type: 'drought',
      context_note: '90-day cumulative rainfall volume',
      is_data_available: true,
    },
    {
      title: 'Seasonal Deficit',
      location: 'Mahoba',
      value: 11.6,
      units: 'percentage',
      delta_percentage: 11.6,
      is_positive_delta: true,
      hazard_type: 'drought',
      context_note: 'Seasonal precipitation departure',
      is_data_available: true,
    },
  ],
  recent_alerts: [],
  active_sources: [],
};

describe('Dashboard Verified Data Hydration Regression Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders verified API values and Verified badges when backendDashboard succeeds with verified data', async () => {
    vi.spyOn(apiService, 'fetchDashboard').mockResolvedValue(MOCK_VERIFIED_DASHBOARD);

    render(<App />);

    // Wait for the verified data to hydrate
    await waitFor(() => {
      expect(screen.getByText('0.0')).toBeInTheDocument();
    });

    // 1. Check all four card values match live backend API values
    expect(screen.getByText('0.0')).toBeInTheDocument();
    expect(screen.getByText('16.8')).toBeInTheDocument();
    expect(screen.getByText('719.7')).toBeInTheDocument();
    expect(screen.getByText('+11.6%')).toBeInTheDocument();

    // 2. Check deltas
    expect(screen.getByText('-100% vs normal')).toBeInTheDocument();
    expect(screen.getByText('-58.2% vs normal')).toBeInTheDocument();
    expect(screen.getByText('+58.7% vs normal')).toBeInTheDocument();

    // 3. Confirm all 4 cards show "Verified" badge
    const verifiedBadges = screen.getAllByText(/^Verified$/i);
    expect(verifiedBadges.length).toBeGreaterThanOrEqual(4);

    // 4. Confirm no card has the "Illustrative" badge
    expect(screen.queryAllByText(/^Illustrative$/i)).toHaveLength(0);

    // 5. Confirm disclaimer matches verified backend disclaimer
    expect(
      screen.getByText(/Grounded in validated CHIRPS v2.0 & NASA GPM observational baselines/i)
    ).toBeInTheDocument();
  });

  it('renders offline fallback values with Illustrative labels when API fetch fails', async () => {
    vi.spyOn(apiService, 'fetchDashboard').mockRejectedValue(new Error('Network offline or timeout'));

    render(<App />);

    // In offline/failure mode, fixture values are rendered
    await waitFor(() => {
      expect(screen.getByText('286')).toBeInTheDocument();
    });

    expect(screen.getByText('512')).toBeInTheDocument();
    expect(screen.getByText('62')).toBeInTheDocument();
    expect(screen.getByText('-72%')).toBeInTheDocument();

    // All 4 summary cards must have the "Illustrative" badge
    const illustrativeBadges = screen.getAllByText(/^Illustrative$/i);
    expect(illustrativeBadges.length).toBeGreaterThanOrEqual(4);

    // No card should claim "Verified"
    expect(screen.queryAllByText(/^Verified$/i)).toHaveLength(0);

    // MainDashboard fallback renders DEMO DATA badge and demonstration disclaimer
    expect(screen.getAllByText(/DEMO DATA/i).length).toBeGreaterThanOrEqual(1);
  });
});
