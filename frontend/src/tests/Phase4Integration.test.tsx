import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { apiService, AssistantChatResponse } from '../services/api';
import App from '../App';

describe('Phase 4 — FastAPI Integration & Gemma 4 Grounded Assistant', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('verifies typed apiService methods construct expected endpoints', async () => {
    const fetchSpy = vi.spyOn(global, 'fetch').mockImplementation((url) => {
      const u = url.toString();
      if (u.includes('/health')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              status: 'healthy',
              project: 'JalRakshak',
              version: '1.0.0-prototype',
              uptime_seconds: 120,
              data_staleness_hours: 2.5,
              stale_detected: false,
              ingestion_status: 'synchronized',
              system_time: '2026-10-29T21:00:00Z',
              is_demo_data: true,
            }),
        } as Response);
      }
      if (u.includes('/risk/flood')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              location: {
                location_id: 'gorakhpur',
                name: 'Gorakhpur',
                hindi_name: 'गोरखपुर',
                latitude: 26.76,
                longitude: 83.37,
                elevation_m: 84.0,
                river_basin: 'Rapti & Rohini',
                region: 'Eastern UP',
                is_pilot: true,
              },
              hazard: 'flood',
              risk_level: 'high',
              assessment_period: 'Last 7 Days',
              generated_at: '2026-10-29T21:00:00Z',
              is_demo_data: true,
              disclaimer: 'Decision-support prototype',
              indicators: [
                {
                  indicator_id: 'gorakhpur_rain_7d',
                  name: '7-Day Cumulative Rainfall',
                  value: 286.0,
                  units: 'mm',
                  category: 'observed_measurement',
                  calculation_window: '7d',
                  reference_baseline: '173.0 mm',
                  observation_timestamp: '2026-10-28',
                  retrieval_timestamp: '2026-10-29',
                  quality_status: 'verified',
                  methodology_version: 'v1.0-transparent',
                  limitations: 'Does not model inundation',
                  is_demo_data: true,
                },
              ],
              sources: [],
              scientific_notes: ['Rainfall alone does not prove river inundation'],
            }),
        } as Response);
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      } as Response);
    });

    const health = await apiService.fetchHealth();
    expect(health.status).toBe('healthy');
    expect(health.is_demo_data).toBe(true);

    const flood = await apiService.fetchFloodRisk('gorakhpur', 7);
    expect(flood.hazard).toBe('flood');
    expect(flood.indicators[0].value).toBe(286.0);

    fetchSpy.mockRestore();
  });

  it('renders grounded assistant response and evidence citations on query', async () => {
    const mockChatResponse: AssistantChatResponse = {
      answer:
        '[GROUNDED DATA EXPLANATION — FASTAPI RISK ENGINE]\n\n• Gorakhpur 7-Day Rainfall: 286.0 mm (+65.3% departure).\n• Scientific Boundary: Rainfall alone does NOT calculate Rapti river stage gauge levels.',
      runtime_status: 'unavailable',
      model_name: 'gemma:4',
      evidence_used: [
        {
          indicator_id: 'gorakhpur_rain_7d',
          name: '7-Day Cumulative Rainfall',
          value: 286.0,
          units: 'mm',
          category: 'observed_measurement',
          observation_period: '7d',
          quality_status: 'verified',
        },
      ],
      citations: ['NASA GPM IMERG Late Run', 'CHIRPS Daily v2.0'],
      relevant_indicators: [],
      data_timestamps: { retrieval_timestamp: '2026-10-29T21:00:00Z' },
      is_demo_data: true,
      limitations: ['Rainfall accumulation indicates meteorological water loading only.'],
      disclaimer: 'JalRakshak Grounded Assistant is an environmental decision-support tool.',
    };

    vi.spyOn(global, 'fetch').mockImplementation((url, opts) => {
      if (url.toString().includes('/assistant/chat')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockChatResponse),
        } as Response);
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      } as Response);
    });

    render(<App />);

    // Navigate to Assistant
    fireEvent.click(screen.getAllByText(/AI Assistant/i)[0]);
    expect(screen.getByText(/JalRakshak Assistant/i)).toBeInTheDocument();

    // Ask a question
    const input = screen.getByPlaceholderText(/Ask a question about rainfall/i);
    fireEvent.change(input, { target: { value: 'Why is flood risk high in Gorakhpur?' } });

    const sendBtn = screen.getByRole('button', { name: /Send query/i });
    fireEvent.click(sendBtn);

    // Wait for the grounded response to appear
    await waitFor(() => {
      expect(
        screen.getByText(/Gorakhpur 7-Day Rainfall: 286.0 mm/i)
      ).toBeInTheDocument();
    });

    // Check evidence indicators badge
    expect(screen.getByText(/7-Day Cumulative Rainfall:/i)).toBeInTheDocument();

    // Check citations
    expect(screen.getByText(/NASA GPM IMERG Late Run/i)).toBeInTheDocument();
  });

  it('handles backend network failure gracefully with honest offline fallback', async () => {
    vi.spyOn(global, 'fetch').mockRejectedValue(new Error('Failed to fetch'));

    render(<App />);
    fireEvent.click(screen.getAllByText(/AI Assistant/i)[0]);

    const input = screen.getByPlaceholderText(/Ask a question about rainfall/i);
    fireEvent.change(input, { target: { value: 'Explain drought in Mahoba' } });

    const sendBtn = screen.getByRole('button', { name: /Send query/i });
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(
        screen.getByText(/DETERMINISTIC OFFLINE MODE/i)
      ).toBeInTheDocument();
    });

    // Verify limitation boundary is retained even in offline fallback
    expect(
      screen.getByText(/characterize meteorological drought only/i)
    ).toBeInTheDocument();
  });
});
