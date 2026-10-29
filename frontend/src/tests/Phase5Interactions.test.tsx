import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import App from '../App';

describe('Phase 5 — Interactive Map, Trends, Preparedness, Data Transparency, & Monitoring', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders interactive map with accessible table toggle and hazard filters', () => {
    render(<App />);
    fireEvent.click(screen.getAllByText(/Risk Map/i)[0]);

    // Check geometry notice
    expect(screen.getByText(/Point centroid coordinates \(WGS84 EPSG:4326\)/i)).toBeInTheDocument();

    // Verify hazard filters
    const floodFilter = screen.getByRole('button', { name: /Flood Focus/i });
    fireEvent.click(floodFilter);
    expect(floodFilter).toHaveClass('bg-rose-500');

    const droughtFilter = screen.getByRole('button', { name: /Drought Focus/i });
    fireEvent.click(droughtFilter);
    expect(droughtFilter).toHaveClass('bg-amber-500');

    // Toggle Accessible Table alternative
    const tableBtn = screen.getByRole('button', { name: /Accessible Table/i });
    fireEvent.click(tableBtn);

    // Verify table headings exist
    expect(screen.getByText(/Accessible District Registry Table/i)).toBeInTheDocument();
    expect(screen.getByText(/Press Enter\/Space on a row to select district/i)).toBeInTheDocument();
    expect(screen.getAllByText(/River Basin/i)[0]).toBeInTheDocument();
    expect(screen.getByText(/SPI-3 Index/i)).toBeInTheDocument();
  });

  it('renders rainfall trends with explicit non-forecast disclaimer and accessible table', () => {
    render(<App />);
    fireEvent.click(screen.getAllByText(/Rainfall & Trends/i)[0]);

    // Check non-forecast scientific notice
    expect(
      screen.getByText(/Does NOT provide or imply a future weather prediction/i)
    ).toBeInTheDocument();

    // Check chart unit disclosures
    expect(screen.getByText(/CHIRPS v2.0 \+ GPM/i)).toBeInTheDocument();

    // Toggle accessible data summary table
    const toggleTableBtn = screen.getByRole('button', { name: /Accessible Table/i });
    fireEvent.click(toggleTableBtn);

    expect(screen.getByText(/Accessible Data Summary/i)).toBeInTheDocument();
    expect(screen.getByText(/Baseline Normal \(mm\)/i)).toBeInTheDocument();
  });

  it('renders preparedness view with official reference disclosures and helplines', () => {
    render(<App />);
    fireEvent.click(screen.getAllByText(/Preparedness/i)[0]);

    // Verify decision-support notice
    expect(
      screen.getByText(/JalRakshak provides verified official reference links and community guidelines/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/PROTOTYPE ADVISORY/i)).toBeInTheDocument();

    // Verify flood guidelines
    expect(
      screen.getByText(/Follow official local warnings and evacuation orders promptly/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Avoid floodwaters: Never walk, wade, or drive through moving water/i)
    ).toBeInTheDocument();

    // Switch to Official Resources
    const resourcesTab = screen.getByRole('button', { name: /Official Resources/i });
    fireEvent.click(resourcesTab);

    // Verify official advisory link badges
    expect(screen.getAllByText(/Official Advisory Reference Link/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/https:\/\/upsdma.up.nic.in/i)).toBeInTheDocument();
  });

  it('renders data sources with complete provenance and 6-part methodology', () => {
    render(<App />);
    fireEvent.click(screen.getAllByText(/Data Sources/i)[0]);

    // Verify provenance integrity notice
    expect(screen.getByText(/Data Provenance Integrity Notice/i)).toBeInTheDocument();

    // Verify sources have status labels
    expect(screen.getByText(/NASA GPM IMERG Late Run/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Local Prototype Fixture \(Not a Live Streaming Feed\)/i)
    ).toBeInTheDocument();

    // Click methodology tab
    const methodTab = screen.getByRole('button', { name: /Processing Pipeline & Math/i });
    fireEvent.click(methodTab);

    expect(screen.getByText(/1. Data Pipeline Ingestion/i)).toBeInTheDocument();
    expect(screen.getByText(/2. Validation, Duplicate Handling, Units & Staleness Tracking/i)).toBeInTheDocument();
    expect(screen.getByText(/4. Standardized Precipitation Index \(SPI-3\) Mathematical Derivation/i)).toBeInTheDocument();
    expect(screen.getByText(/5. Indicator Boundaries: What Indicators Do & Do Not Measure/i)).toBeInTheDocument();
    expect(screen.getByText(/6. Legal & Operational Authority/i)).toBeInTheDocument();
  });

  it('renders system monitoring with 4 distinct diagnostic tiers', () => {
    render(<App />);
    fireEvent.click(screen.getAllByText(/System Monitoring/i)[0]);

    // Check 4-tier separation notice
    expect(screen.getByText(/Observability & Separation of Concerns/i)).toBeInTheDocument();

    // Check FastAPI card
    expect(screen.getAllByText(/FastAPI Backend/i)[0]).toBeInTheDocument();

    // Check distinct Gemma 4 runtime card
    expect(screen.getByText(/Gemma 4 Runtime/i)).toBeInTheDocument();
    expect(screen.getByText(/Deterministic Engine/i)).toBeInTheDocument();

    // Check Data Freshness card
    expect(screen.getByText(/11.2 Hours Age/i)).toBeInTheDocument();
    expect(screen.getByText(/Fresh \(< 24h Threshold\)/i)).toBeInTheDocument();

    // Check Pipeline Mode card
    expect(screen.getAllByText(/Local Reproducible Fixtures/i)[0]).toBeInTheDocument();
  });
});
