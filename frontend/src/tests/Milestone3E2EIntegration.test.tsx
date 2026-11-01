import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import App from '../App';
import { apiService } from '../services/api';

describe('Milestone 3 — End-to-End Integration & Multi-District Verification', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(apiService, 'fetchRegions').mockResolvedValue([
      {
        id: 'district-gorakhpur',
        code: 'IN-UP-GOR',
        name: 'Gorakhpur',
        region_type: 'district',
        parent_id: 'state-uttar-pradesh',
        country_code: 'IN',
        state_code: 'UP',
        is_active: true,
        supported_hazards: [{ code: 'flood', status: 'pilot', is_enabled: true }],
        metadata: { legacy_id: 'gorakhpur', hindi_name: 'गोरखपुर', river_basin: 'Rapti Basin' },
      },
      {
        id: 'district-mahoba',
        code: 'IN-UP-MAH',
        name: 'Mahoba',
        region_type: 'district',
        parent_id: 'state-uttar-pradesh',
        country_code: 'IN',
        state_code: 'UP',
        is_active: true,
        supported_hazards: [{ code: 'drought', status: 'pilot', is_enabled: true }],
        metadata: { legacy_id: 'mahoba', hindi_name: 'महोबा', river_basin: 'Ken-Betwa' },
      },
      {
        id: 'district-lucknow',
        code: 'IN-UP-LUC',
        name: 'Lucknow',
        region_type: 'district',
        parent_id: 'state-uttar-pradesh',
        country_code: 'IN',
        state_code: 'UP',
        is_active: true,
        supported_hazards: [],
        metadata: { legacy_id: 'lucknow', hindi_name: 'लखनऊ', river_basin: 'Gomti Basin' },
      },
      {
        id: 'district-patna',
        code: 'IN-BR-PAT',
        name: 'Patna',
        region_type: 'district',
        parent_id: 'state-bihar',
        country_code: 'IN',
        state_code: 'BR',
        is_active: true,
        supported_hazards: [],
        metadata: { legacy_id: 'patna', hindi_name: 'पटना', river_basin: 'Ganga Basin' },
      },
    ] as any);
  });

  it('demonstrates end-to-end candidate district selection without data bleed or pilot score inheritance', async () => {
    render(<App />);

    // 1. By default, Gorakhpur is active
    expect(screen.getAllByText(/Gorakhpur/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Current Rainfall/i)).toBeInTheDocument();

    // 2. Open cascading region selector
    const selectorBtn = screen.getByRole('button', { name: /UP :/i });
    fireEvent.click(selectorBtn);

    // 3. Switch state tab to Bihar
    const biharTab = screen.getByRole('button', { name: /Bihar \(38\)/i });
    fireEvent.click(biharTab);

    // 4. Select Patna candidate district
    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /Patna/i }).length).toBeGreaterThan(0);
    });
    const patnaBtns = screen.getAllByRole('button', { name: /Patna/i });
    fireEvent.click(patnaBtns[0]);

    // 5. Verify Header updates to Bihar : Patna with Pending badge
    expect(screen.getByRole('button', { name: /BR : Patna/i })).toBeInTheDocument();
    expect(screen.getAllByText(/Pending/i).length).toBeGreaterThan(0);

    // 6. Verify Main Dashboard displays the Candidate District Isolation Banner
    expect(screen.getByText(/Candidate District • Ingestion Pending/i)).toBeInTheDocument();
    expect(screen.getByText(/Scientific Integrity & Data Isolation Notice/i)).toBeInTheDocument();
    expect(
      screen.getByText(/This district never inherits or interpolates risk scores from Gorakhpur or Mahoba/i)
    ).toBeInTheDocument();

    // 7. Verify Metric Cards refreshed to honest Data Pending states (zero data bleed)
    expect(screen.getAllByText(/Data Pending/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Station telemetry stream unlinked/i)).toBeInTheDocument();
    expect(screen.getByText(/Ingestion pipeline awaiting execution/i)).toBeInTheDocument();
    expect(screen.getByText(/30-year climatology uncalibrated/i)).toBeInTheDocument();
    expect(screen.getByText(/Zero data bleed from pilot models/i)).toBeInTheDocument();

    // 8. Verify Recent Rainfall Trend displays candidate pending empty state rather than leaking Gorakhpur's chart
    expect(
      screen.getByText(/No Historical Telemetry Ingested for Patna/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/JalRakshak integrity rules strictly prevent proxy interpolation from Gorakhpur or Mahoba/i)
    ).toBeInTheDocument();
  });

  it('restores calibrated flood metrics when switching from candidate district back to Gorakhpur', async () => {
    render(<App />);

    // Open selector and switch to Lucknow
    const selectorBtn = screen.getByRole('button', { name: /UP :/i });
    fireEvent.click(selectorBtn);
    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /Lucknow/i }).length).toBeGreaterThan(0);
    });
    fireEvent.click(screen.getAllByRole('button', { name: /Lucknow/i })[0]);

    // Verify candidate banner is present
    expect(screen.getByText(/Candidate District • Ingestion Pending/i)).toBeInTheDocument();

    // Click quick launcher to focus Gorakhpur
    const gorakhpurLauncher = screen.getByRole('button', { name: /Gorakhpur Flood Pilot/i });
    fireEvent.click(gorakhpurLauncher);

    // Verify pilot restored
    expect(screen.getByText(/PILOT: UP-2026/i)).toBeInTheDocument();
    expect(screen.getByText(/286/i)).toBeInTheDocument(); // Gorakhpur 7d rain
    expect(screen.getByText(/512/i)).toBeInTheDocument(); // Gorakhpur 30d rain
  });

  it('safely handles specialized assessment views when a candidate district is selected', async () => {
    render(<App />);

    // Open selector and pick Lucknow
    const selectorBtn = screen.getByRole('button', { name: /UP :/i });
    fireEvent.click(selectorBtn);
    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /Lucknow/i }).length).toBeGreaterThan(0);
    });
    fireEvent.click(screen.getAllByRole('button', { name: /Lucknow/i })[0]);

    // 1. Navigate to Flood Assessment
    fireEvent.click(screen.getAllByText(/Flood Assessment/i)[0]);
    // Verifies the hazard scope alert is shown informing the user Lucknow is unconfigured
    expect(screen.getByText(/Hazard Pilot Scope:/i)).toBeInTheDocument();
    expect(screen.getByText(/Gorakhpur is currently the active flood pilot/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Lucknow/i).length).toBeGreaterThan(0);

    // 2. Navigate to Drought Assessment
    fireEvent.click(screen.getAllByText(/Drought Assessment/i)[0]);
    // Verifies the hazard scope alert is shown informing the user Lucknow is unconfigured
    expect(screen.getByText(/Hazard Pilot Scope:/i)).toBeInTheDocument();
    expect(screen.getByText(/Mahoba is currently the active drought pilot/i)).toBeInTheDocument();

    // 3. Navigate to Rainfall & Trends
    fireEvent.click(screen.getAllByText(/Rainfall & Trends/i)[0]);
    expect(
      screen.getByText(/No Historical Precipitation Telemetry Ingested for Lucknow/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/candidate districts never inherit or interpolate observations from Gorakhpur or Mahoba/i)
    ).toBeInTheDocument();
  });
});
