import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { DataSourcesView } from '../views/DataSourcesView';
import { DataProvenanceBadge } from '../components/common/DataProvenanceBadge';
import { apiService, DatasetUploadResponse, UploadHistoryItem } from '../services/api';

describe('Stage 3 — Scientific Dataset Uploads & Quarantine Validation', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(apiService, 'fetchSources').mockResolvedValue([]);
    vi.spyOn(apiService, 'fetchUploadHistory').mockResolvedValue([
      {
        upload_id: 'up_test123456',
        filename: 'gorakhpur_test_precip.csv',
        file_type: 'CSV',
        target_region_id: 'district-gorakhpur',
        records_count: 365,
        status: 'VALIDATED',
        file_size_bytes: 14200,
        uploaded_at: '2026-10-31T12:00:00Z',
      },
    ]);
  });

  it('renders MANUAL_UPLOAD data mode in DataProvenanceBadge', () => {
    render(<DataProvenanceBadge mode="MANUAL_UPLOAD" />);
    expect(screen.getByText('MANUAL UPLOAD')).toBeInTheDocument();
  });

  it('renders the Scientific Uploads tab and allows tab switching', async () => {
    render(<DataSourcesView />);

    // Check tab button exists
    const uploadTabButton = screen.getByRole('button', { name: /scientific uploads/i });
    expect(uploadTabButton).toBeInTheDocument();

    // Click tab
    fireEvent.click(uploadTabButton);

    // Verify upload panel is rendered
    expect(
      screen.getByText(/quarantine sandbox & true binary content inspection/i)
    ).toBeInTheDocument();
    expect(screen.getByText('Upload Environmental Dataset')).toBeInTheDocument();
  });

  it('displays validation report upon successful dataset upload', async () => {
    const mockUploadResponse: DatasetUploadResponse = {
      upload_id: 'up_abc12345678',
      filename: 'station_rain_2024.csv',
      status: 'VALIDATED',
      message: 'Dataset successfully verified and registered.',
      uploaded_at: '2026-10-31T15:00:00Z',
      validation_report: {
        is_valid: true,
        file_type: 'CSV',
        mime_detected: 'text/csv',
        file_size_bytes: 2048,
        sha256_hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        target_region_id: 'district-gorakhpur',
        data_mode: 'MANUAL_UPLOAD',
        temporal_semantics: 'daily_accumulation',
        total_records: 30,
        valid_records: 29,
        missing_records: 1,
        extreme_records: 0,
        date_range: { start: '2024-08-01', end: '2024-08-30' },
        mean_value: 12.4,
        max_value: 45.0,
        min_value: 0.0,
        warnings: [],
        errors: [],
        metadata: {},
      },
    };

    vi.spyOn(apiService, 'uploadScientificDataset').mockResolvedValue(mockUploadResponse);

    render(<DataSourcesView />);

    // Switch to Uploads tab
    fireEvent.click(screen.getByRole('button', { name: /scientific uploads/i }));

    // Mock selecting a file
    const file = new File(['date,rainfall_mm\n2024-08-01,10.0\n'], 'station_rain_2024.csv', {
      type: 'text/csv',
    });
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).toBeInTheDocument();

    fireEvent.change(fileInput, {
      target: { files: [file] },
    });

    // Wait for file selection to be displayed
    await waitFor(() => {
      expect(screen.getByText('station_rain_2024.csv')).toBeInTheDocument();
    });

    // Submit form via submit event
    const form = fileInput.closest('form')!;
    fireEvent.submit(form);

    // Verify report card is displayed
    await waitFor(() => {
      expect(screen.getByText(/validation report: station_rain_2024\.csv/i)).toBeInTheDocument();
      expect(screen.getAllByText('VALIDATED').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('MANUAL UPLOAD').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('30')).toBeInTheDocument(); // total records
      expect(screen.getByText('29')).toBeInTheDocument(); // valid records
    });
  });

  it('renders upload history in registry table', async () => {
    render(<DataSourcesView />);

    // Switch to Uploads tab
    fireEvent.click(screen.getByRole('button', { name: /scientific uploads/i }));

    await waitFor(() => {
      expect(screen.getByText('gorakhpur_test_precip.csv')).toBeInTheDocument();
      expect(screen.getByText('365')).toBeInTheDocument();
    });
  });

  it('triggers quarantine cleanup when cleanup button is clicked', async () => {
    vi.spyOn(apiService, 'cleanupQuarantine').mockResolvedValue({
      deleted_files_count: 2,
      reclaimed_bytes: 4096,
      current_storage_bytes: 8192,
    });

    render(<DataSourcesView />);

    // Switch to Uploads tab
    fireEvent.click(screen.getByRole('button', { name: /scientific uploads/i }));

    const cleanupBtn = screen.getByRole('button', { name: /purge expired quarantine/i });
    expect(cleanupBtn).toBeInTheDocument();

    fireEvent.click(cleanupBtn);

    await waitFor(() => {
      expect(screen.getByText(/quarantine purged: 2 files removed/i)).toBeInTheDocument();
    });
  });
});
