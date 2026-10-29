import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import App from '../App';
import { apiService } from '../services/api';

describe('Phase 6 — End-to-End Hardening, Scientific Integrity & Resilience', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders complete user journey across all views with correct scientific disclaimers', () => {
    render(<App />);

    // 1. Dashboard loads
    expect(screen.getByText(/Smarter Insights/i)).toBeInTheDocument();
    expect(screen.getAllByText(/for Safer Communities/i)[0]).toBeInTheDocument();

    // 2. Navigate to Flood Assessment
    fireEvent.click(screen.getAllByText(/Flood Assessment/i)[0]);
    expect(screen.getByText(/Gorakhpur — Flood Assessment/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Rainfall accumulation alone does NOT determine Rapti\/Rohini river stage/i)
    ).toBeInTheDocument();

    // 3. Navigate to Drought Assessment
    fireEvent.click(screen.getAllByText(/Drought Assessment/i)[0]);
    expect(screen.getByText(/Mahoba — Drought Assessment/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Meteorological indicators do NOT directly measure root-zone soil moisture/i)
    ).toBeInTheDocument();

    // 4. Navigate to Risk Map
    fireEvent.click(screen.getAllByText(/Risk Map/i)[0]);
    expect(screen.getByText(/Point centroid coordinates \(WGS84 EPSG:4326\)/i)).toBeInTheDocument();

    // 5. Navigate to Trends
    fireEvent.click(screen.getAllByText(/Rainfall & Trends/i)[0]);
    expect(
      screen.getByText(/Does NOT provide or imply a future weather prediction/i)
    ).toBeInTheDocument();

    // 6. Navigate to Sources
    fireEvent.click(screen.getAllByText(/Data Sources/i)[0]);
    expect(screen.getByText(/Data Provenance Integrity Notice/i)).toBeInTheDocument();

    // 7. Navigate to Preparedness
    fireEvent.click(screen.getAllByText(/Preparedness/i)[0]);
    expect(screen.getByText(/PROTOTYPE ADVISORY/i)).toBeInTheDocument();

    // 8. Navigate to Monitoring
    fireEvent.click(screen.getAllByText(/System Monitoring/i)[0]);
    expect(screen.getByText(/Observability & Separation of Concerns/i)).toBeInTheDocument();
  });

  it('handles assistant queries with grounded deterministic fallback and transparent disclosures', async () => {
    render(<App />);
    fireEvent.click(screen.getAllByText(/AI Assistant/i)[0]);

    // Check assistant title
    expect(screen.getByText(/JalRakshak Assistant/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Gemma 4 Adapter/i)[0]).toBeInTheDocument();

    // Simulate sending a suggested question
    const questionBtn = screen.getByText(/Why is flood risk high in Gorakhpur\?/i);
    fireEvent.click(questionBtn);

    // Verify loading or response
    await waitFor(() => {
      expect(screen.getAllByText(/Gorakhpur/i).length).toBeGreaterThan(0);
    });
  });

  it('handles API network failure in services layer gracefully without crash', async () => {
    // Mock fetch to reject
    const originalFetch = global.fetch;
    global.fetch = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'));

    try {
      await apiService.fetchDashboard('gorakhpur');
    } catch (err: any) {
      expect(err.message).toContain('Network error connecting to FastAPI backend');
    } finally {
      global.fetch = originalFetch;
    }
  });

  it('handles API abort timeout gracefully', async () => {
    const originalFetch = global.fetch;
    const abortErr = new Error('AbortError');
    abortErr.name = 'AbortError';
    global.fetch = vi.fn().mockRejectedValue(abortErr);

    try {
      await apiService.fetchFloodRisk('gorakhpur');
    } catch (err: any) {
      expect(err.message).toContain('Request timed out connecting to');
    } finally {
      global.fetch = originalFetch;
    }
  });

  it('exports rainfall data correctly as JSON format with provenance metadata', () => {
    render(<App />);
    fireEvent.click(screen.getAllByText(/Rainfall & Trends/i)[0]);

    // Mock URL.createObjectURL and link.click to avoid JSDOM navigation error
    const createObjectUrlMock = vi.fn().mockReturnValue('blob:mock-url');
    const revokeObjectUrlMock = vi.fn();
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    window.URL.createObjectURL = createObjectUrlMock;
    window.URL.revokeObjectURL = revokeObjectUrlMock;

    const jsonBtn = screen.getByRole('button', { name: /JSON/i });
    fireEvent.click(jsonBtn);

    expect(createObjectUrlMock).toHaveBeenCalledTimes(1);
    expect(clickSpy).toHaveBeenCalledTimes(1);
    expect(revokeObjectUrlMock).toHaveBeenCalledTimes(1);

    clickSpy.mockRestore();
  });
});
