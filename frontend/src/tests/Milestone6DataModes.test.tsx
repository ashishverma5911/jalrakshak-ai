import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { DataProvenanceBadge } from '../components/common/DataProvenanceBadge';
import App from '../App';
import { apiService } from '../services/api';

describe('Milestone 6 — Real-World Data Modes & Data Provenance Badges', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders all 5 distinct data modes correctly in DataProvenanceBadge', () => {
    // 1. LIVE_VERIFIED
    const { unmount: u1 } = render(<DataProvenanceBadge mode="LIVE_VERIFIED" />);
    expect(screen.getByText('LIVE VERIFIED DATA')).toBeInTheDocument();
    u1();

    // 2. CACHED_VERIFIED
    const { unmount: u2 } = render(<DataProvenanceBadge mode="CACHED_VERIFIED" />);
    expect(screen.getByText('CACHED VERIFIED DATA')).toBeInTheDocument();
    u2();

    // 3. DEMONSTRATION
    const { unmount: u3 } = render(<DataProvenanceBadge mode="DEMONSTRATION" />);
    expect(screen.getByText('DEMO DATA')).toBeInTheDocument();
    u3();

    // 4. DATA_PENDING
    const { unmount: u4 } = render(<DataProvenanceBadge mode="DATA_PENDING" />);
    expect(screen.getByText('DATA PENDING')).toBeInTheDocument();
    u4();

    // 5. DATA_STALE
    const { unmount: u5 } = render(<DataProvenanceBadge mode="DATA_STALE" />);
    expect(screen.getByText('DATA STALE')).toBeInTheDocument();
    u5();
  });

  it('interactively toggles the provenance disclosure card with scientific metadata', () => {
    render(
      <DataProvenanceBadge
        mode="CACHED_VERIFIED"
        source="CHIRPS Daily v2.0 (0.05°)"
        datasetVersion="v2.0 station-blended"
        spatialResolution="0.05° (~5.3 km gridded)"
        observationPeriod="2015–2026 Continuous Record"
        limitations="Area-weighted polygon intersection over official boundary. Local rainfall != Rapti gauge depth."
      />
    );

    const badgeButton = screen.getByText('CACHED VERIFIED DATA');
    expect(screen.queryByText(/Dataset Provenance/i)).not.toBeInTheDocument();

    // Click to open disclosure
    fireEvent.click(badgeButton);
    expect(screen.getByText(/Dataset Provenance/i)).toBeInTheDocument();
    expect(screen.getByText(/CHIRPS Daily v2.0/i)).toBeInTheDocument();
    expect(screen.getByText(/v2.0 station-blended/i)).toBeInTheDocument();
    expect(screen.getByText(/0.05° \(~5.3 km gridded\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Local rainfall != Rapti gauge depth/i)).toBeInTheDocument();

    // Click again to close
    fireEvent.click(badgeButton);
    expect(screen.queryByText(/Dataset Provenance/i)).not.toBeInTheDocument();
  });

  it('candidate district displays DATA PENDING without data bleed from pilots', async () => {
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
        metadata: { legacy_id: 'gorakhpur', hindi_name: 'गोरखपुर' },
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
        metadata: { legacy_id: 'lucknow', hindi_name: 'लखनऊ' },
      },
    ] as any);

    render(<App />);

    // Initial state: Gorakhpur pilot displays verified or demo badge
    await waitFor(() => {
      expect(screen.getAllByText(/Gorakhpur/i).length).toBeGreaterThan(0);
    });

    // Open Region Selector
    const selectorBtn = screen.getByRole('button', { name: /UP :/i });
    fireEvent.click(selectorBtn);

    // Switch to Lucknow
    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /Lucknow/i }).length).toBeGreaterThan(0);
    });
    const lucknowBtns = screen.getAllByRole('button', { name: /Lucknow/i });
    fireEvent.click(lucknowBtns[0]);

    // Verify candidate district displays isolation banner & zero data bleed
    await waitFor(() => {
      expect(screen.getByText(/Candidate District • Ingestion Pending/i)).toBeInTheDocument();
      expect(screen.getByText(/Zero data bleed from pilot models/i)).toBeInTheDocument();
      expect(screen.getAllByText(/DATA PENDING/i).length).toBeGreaterThan(0);
    });
  });
});
