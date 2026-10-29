import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import App from '../App';

describe('JalRakshak AI — Application Shell & Design System', () => {
  it('renders the JalRakshak AI branding and subtitle', () => {
    render(<App />);
    const brandElements = screen.getAllByText(/JalRakshak/i);
    expect(brandElements.length).toBeGreaterThan(0);

    const subtitleElements = screen.getAllByText(/For Safer Communities/i);
    expect(subtitleElements.length).toBeGreaterThan(0);
  });

  it('renders all 9 primary navigation destinations in the sidebar', () => {
    render(<App />);
    const navTitles = [
      'Dashboard',
      'Flood Assessment',
      'Drought Assessment',
      'Risk Map',
      'Rainfall & Trends',
      'AI Assistant',
      'Preparedness',
      'Data Sources',
      'System Monitoring',
    ];

    navTitles.forEach((title) => {
      const match = screen.getAllByText(new RegExp(`^${title}$`, 'i'));
      expect(match.length).toBeGreaterThan(0);
    });
  });

  it('navigates to Flood Assessment and switches focus to Gorakhpur', () => {
    render(<App />);
    const floodNavBtn = screen.getAllByText(/Flood Assessment/i)[0];
    fireEvent.click(floodNavBtn);

    expect(screen.getByText(/Gorakhpur — Flood Assessment/i)).toBeInTheDocument();
    const highBadges = screen.getAllByText(/HIGH/i);
    expect(highBadges.length).toBeGreaterThan(0);
  });

  it('navigates to Drought Assessment and shows Mahoba indicators', () => {
    render(<App />);
    const droughtNavBtn = screen.getAllByText(/Drought Assessment/i)[0];
    fireEvent.click(droughtNavBtn);

    expect(screen.getByText(/Mahoba — Drought Assessment/i)).toBeInTheDocument();
    const modBadges = screen.getAllByText(/MODERATE/i);
    expect(modBadges.length).toBeGreaterThan(0);
  });

  it('opens and closes the search modal', () => {
    render(<App />);
    const searchTrigger = screen.getByText(/Search location/i);
    fireEvent.click(searchTrigger);

    expect(screen.getByPlaceholderText(/Type district or page/i)).toBeInTheDocument();
    expect(screen.getByText(/Tip: Press ESC to close/i)).toBeInTheDocument();
  });

  it('opens alerts drawer upon clicking notifications bell', () => {
    render(<App />);
    const bellBtn = screen.getByLabelText(/Alerts & Updates/i);
    fireEvent.click(bellBtn);

    expect(screen.getByText(/Alerts & Real-Time Updates/i)).toBeInTheDocument();
    expect(screen.getAllByText(/High Rainfall Alert/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Drought Watch/i).length).toBeGreaterThan(0);
  });
});
