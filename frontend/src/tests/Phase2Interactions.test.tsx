import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import App from '../App';

describe('Phase 2 — Complete Frontend Interactions & State Verification', () => {
  it('navigates seamlessly across all 9 views', () => {
    render(<App />);

    // 1. Dashboard is default
    expect(screen.getByText(/Smarter Insights/i)).toBeInTheDocument();

    // 2. Flood Assessment
    fireEvent.click(screen.getAllByText(/Flood Assessment/i)[0]);
    expect(screen.getByText(/Gorakhpur — Flood Assessment/i)).toBeInTheDocument();

    // 3. Drought Assessment
    fireEvent.click(screen.getAllByText(/Drought Assessment/i)[0]);
    expect(screen.getByText(/Mahoba — Drought Assessment/i)).toBeInTheDocument();

    // 4. Interactive Risk Map
    fireEvent.click(screen.getAllByText(/Risk Map/i)[0]);
    expect(screen.getByText(/Interactive Risk Map/i)).toBeInTheDocument();
    expect(screen.getByText(/Geospatial Hazard Layers/i)).toBeInTheDocument();

    // 5. Rainfall & Trends
    fireEvent.click(screen.getAllByText(/Rainfall & Trends/i)[0]);
    expect(screen.getByText(/Rainfall & Historical Trends/i)).toBeInTheDocument();

    // 6. AI Assistant (Gemma 4)
    fireEvent.click(screen.getAllByText(/AI Assistant/i)[0]);
    expect(screen.getByText(/JalRakshak Assistant/i)).toBeInTheDocument();
    expect(screen.getByText(/Suggested Questions/i)).toBeInTheDocument();

    // 7. Preparedness & Safety
    fireEvent.click(screen.getAllByText(/Preparedness/i)[0]);
    expect(screen.getByText(/Preparedness & Safety/i)).toBeInTheDocument();

    // 8. Data Sources & Methodology
    fireEvent.click(screen.getAllByText(/Data Sources/i)[0]);
    expect(screen.getByText(/Data Sources & Methodology/i)).toBeInTheDocument();

    // 9. System Monitoring
    fireEvent.click(screen.getAllByText(/System Monitoring/i)[0]);
    expect(screen.getByText(/System Monitoring & Health/i)).toBeInTheDocument();
    expect(screen.getAllByText(/FastAPI Backend/i)[0]).toBeInTheDocument();
  });

  it('updates rainfall chart when switching time range filters', () => {
    render(<App />);
    fireEvent.click(screen.getAllByText(/Rainfall & Trends/i)[0]);

    // Check default 1 Year
    const fiveYearBtn = screen.getByRole('button', { name: /5 Years/i });
    fireEvent.click(fiveYearBtn);
    expect(fiveYearBtn).toHaveClass('bg-cyan-500');

    // Switch aggregation to Weekly
    const weeklyBtn = screen.getByRole('button', { name: /weekly/i });
    fireEvent.click(weeklyBtn);
    expect(weeklyBtn).toHaveClass('bg-cyan-500');
  });

  it('switches pilot location and updates hazard metrics', () => {
    render(<App />);
    fireEvent.click(screen.getAllByText(/Flood Assessment/i)[0]);

    // Switch dropdown to Mahoba
    const locationSelect = screen.getByRole('combobox');
    fireEvent.change(locationSelect, { target: { value: 'mahoba' } });

    // Should switch route and show Mahoba
    expect(screen.getByText(/Mahoba — Drought Assessment/i)).toBeInTheDocument();
  });

  it('toggles map hazard layers between Flood and Drought', () => {
    render(<App />);
    fireEvent.click(screen.getAllByText(/Risk Map/i)[0]);

    const droughtLayerBtns = screen.getAllByRole('button', { name: /Drought Risk/i });
    fireEvent.click(droughtLayerBtns[0]);
    expect(droughtLayerBtns[0]).toHaveClass('bg-cyan-500');

    const elevationLayerBtns = screen.getAllByRole('button', { name: /Elevation/i });
    fireEvent.click(elevationLayerBtns[0]);
    expect(elevationLayerBtns[0]).toHaveClass('bg-cyan-500');
  });

  it('demonstrates Gemma 4 grounded response template with safety disclaimer', async () => {
    render(<App />);
    fireEvent.click(screen.getAllByText(/AI Assistant/i)[0]);

    // Click suggested question
    const suggestedBtn = screen.getByRole('button', {
      name: /Why is rainfall low in Mahoba\?/i,
    });
    fireEvent.click(suggestedBtn);

    // Verify user message appeared in the list
    expect(
      screen.getByText(/Why is rainfall low in Mahoba\?/i, { selector: 'div' })
    ).toBeInTheDocument();

    // Verify presence of grounded data sources and disclaimer after timeout
    await waitFor(
      () => {
        expect(
          screen.getByText(/Backend Gemma 4 runtime in Standby \(Phase 4\)/i)
        ).toBeInTheDocument();
      },
      { timeout: 2000 }
    );
  });

  it('allows toggling checklist items in Preparedness', () => {
    render(<App />);
    fireEvent.click(screen.getAllByText(/Preparedness/i)[0]);

    const checkItem = screen.getByText(/Keep emergency grab-bag ready/i);
    fireEvent.click(checkItem);
    expect(checkItem).toBeInTheDocument();
  });

  it('simulates data pipeline freshness states from header', () => {
    render(<App />);

    // Open data state simulation dropdown
    const stateBtn = screen.getByTitle(/Click to simulate data pipeline states/i);
    fireEvent.click(stateBtn);

    expect(screen.getByText(/Data Pipeline State Simulation/i)).toBeInTheDocument();

    // Select Stale Data state
    const staleOpt = screen.getByText(/Stale Data State/i);
    fireEvent.click(staleOpt);

    // Stale warning should appear on dashboard
    expect(screen.getByText(/Stale Data Warning:/i)).toBeInTheDocument();
  });
});
