import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AppProvider } from '../context/AppContext';
import { RegionSelector } from '../components/common/RegionSelector';
import { MainDashboardView } from '../views/MainDashboardView';
import { apiService } from '../services/api';

describe('Milestone 2 — Dynamic Multi-Region & District Selector', () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
        supported_hazards: [
          { code: 'flood', status: 'pilot', is_enabled: true }
        ],
        metadata: { legacy_id: 'gorakhpur', hindi_name: 'गोरखपुर', river_basin: 'Rapti Basin' }
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
        supported_hazards: [
          { code: 'flood', status: 'not_configured', is_enabled: false }
        ],
        metadata: { legacy_id: 'lucknow', hindi_name: 'लखनऊ', river_basin: 'Gomti River Basin' }
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
        supported_hazards: [
          { code: 'flood', status: 'not_configured', is_enabled: false }
        ],
        metadata: { legacy_id: 'patna', hindi_name: 'पटना', river_basin: 'Ganga-Son Basin' }
      }
    ]);
  });

  it('renders the selector button with active pilot badge by default', () => {
    render(
      <AppProvider>
        <RegionSelector />
      </AppProvider>
    );

    expect(screen.getByText(/UP :/i)).toBeInTheDocument();
    expect(screen.getByText('Gorakhpur')).toBeInTheDocument();
    expect(screen.getByText('Pilot')).toBeInTheDocument();
  });

  it('opens cascading dropdown and allows state switching between UP and Bihar', async () => {
    render(
      <AppProvider>
        <RegionSelector />
      </AppProvider>
    );

    // Click trigger button
    const trigger = screen.getByRole('button', { name: /UP :/i });
    fireEvent.click(trigger);

    // Verify popover header and state buttons
    expect(screen.getByText(/Administrative Hierarchy/i)).toBeInTheDocument();
    const upTab = screen.getByRole('button', { name: /Uttar Pradesh \(75\)/i });
    const brTab = screen.getByRole('button', { name: /Bihar \(38\)/i });
    expect(upTab).toBeInTheDocument();
    expect(brTab).toBeInTheDocument();

    // Click Bihar tab
    fireEvent.click(brTab);
    expect(apiService.fetchRegions).toHaveBeenCalledWith({
      region_type: 'district',
      state: 'BR'
    });
  });

  it('selects a candidate district and displays the ingestion pending badge', async () => {
    render(
      <AppProvider>
        <div>
          <RegionSelector />
          <MainDashboardView />
        </div>
      </AppProvider>
    );

    // Open dropdown
    const trigger = screen.getByRole('button', { name: /UP :/i });
    fireEvent.click(trigger);

    // Wait for districts to populate
    await waitFor(() => {
      expect(screen.getByText('Lucknow')).toBeInTheDocument();
    });

    // Select Lucknow
    const lucknowBtns = screen.getAllByRole('button', { name: /Lucknow/i });
    fireEvent.click(lucknowBtns[0]);

    // Now trigger should display Pending badge and Candidate Ingestion notice in Dashboard
    await waitFor(() => {
      expect(screen.getByText(/Candidate District • Ingestion Pending/i)).toBeInTheDocument();
      expect(screen.getByText(/Scientific Integrity & Data Isolation Notice/i)).toBeInTheDocument();
    });
  });
});
