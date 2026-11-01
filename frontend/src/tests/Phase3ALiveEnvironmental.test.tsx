import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DataProvenanceBadge } from '../components/common/DataProvenanceBadge';
import { DataSourcesView } from '../views/DataSourcesView';
import { AppProvider } from '../context/AppContext';

describe('Phase 3A — Live Environmental Data Integration', () => {
  it('renders LIVE_MODEL badge with distinct styling and active indicator', () => {
    const { container } = render(
      <DataProvenanceBadge
        mode="LIVE_MODEL"
        source="Open-Meteo ECMWF IFS / GFS Blend"
        datasetVersion="Forecast v1.0"
        spatialResolution="0.1° Representative Point"
      />
    );

    expect(screen.getByText('LIVE MODEL DATA')).toBeInTheDocument();
    const button = container.querySelector('button');
    expect(button?.className).toContain('bg-emerald-500/15');
    const pulseDot = container.querySelector('.animate-pulse');
    expect(pulseDot).not.toBeNull();
  });

  it('renders PROVIDER_ERROR badge when external source is unreachable', () => {
    const { container } = render(
      <DataProvenanceBadge
        mode="PROVIDER_ERROR"
        source="Open-Meteo API"
      />
    );

    expect(screen.getByText('PROVIDER ERROR')).toBeInTheDocument();
    const button = container.querySelector('button');
    expect(button?.className).toContain('bg-rose-500/15');
  });

  it('renders NWP FORECAST badge for future timestamps', () => {
    const { container } = render(
      <DataProvenanceBadge
        mode="FORECAST"
        source="Open-Meteo 7-Day Forecast"
      />
    );

    expect(screen.getByText('NWP FORECAST')).toBeInTheDocument();
    const button = container.querySelector('button');
    expect(button?.className).toContain('bg-indigo-500/15');
  });

  it('lists Open-Meteo in DataSourcesView with CC-BY 4.0 attribution and representative-point note', () => {
    render(
      <AppProvider>
        <DataSourcesView />
      </AppProvider>
    );

    expect(screen.getByText('Open-Meteo Weather Forecast (NWP)')).toBeInTheDocument();
    expect(screen.getByText(/Open-Meteo GmbH \/ ECMWF \/ GFS Blend/i)).toBeInTheDocument();
  });
});
