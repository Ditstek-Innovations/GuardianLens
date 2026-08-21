import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ModelTrainingPage } from './ModelTrainingPage';

vi.mock('../api/useModelTraining', () => ({
  useModelTraining: () => ({
    isPending: false,
    isError: false,
    refetch: vi.fn(),
    data: {
      reviewed: 14,
      eligible: 12,
      excluded: 2,
      by_class: { bottle: 7, cell_phone: 5 },
      worker_state: 'training',
      worker_detail: null,
      dataset_hash: 'abc123',
      candidate_path: null,
      deployed: false,
      minimum_samples: 20,
      current_epoch: 8,
      total_epochs: 40,
      progress_percent: 20,
      updated_at: '2026-08-21T06:00:00Z',
    },
  }),
}));

describe('ModelTrainingPage', () => {
  it('shows real feedback counts and worker epoch progress', () => {
    render(<ModelTrainingPage />);

    expect(screen.getByRole('heading', { name: 'Model training' })).toBeInTheDocument();
    expect(screen.getByText('Training in progress')).toBeInTheDocument();
    expect(screen.getByText('Epoch 8 of 40 (20%)')).toBeInTheDocument();
    expect(screen.getByText('bottle: 7')).toBeInTheDocument();
    expect(screen.getByText(/live detector changes only after validation/i)).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '20');
  });
});
