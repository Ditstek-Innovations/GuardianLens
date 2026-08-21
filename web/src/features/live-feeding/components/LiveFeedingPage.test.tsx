import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useQueueQuery } from '@/features/review-queue';
import { useAuth } from '@/hooks/useAuth';
import { makeQueuePage } from '@/test/factories';

import { LiveFeedingPage } from './LiveFeedingPage';

vi.mock('@/features/review-queue', () => ({ useQueueQuery: vi.fn() }));
vi.mock('@/hooks/useAuth', () => ({ useAuth: vi.fn() }));
vi.mock('@/hooks/useToast', () => ({ useToast: () => ({ showToast: vi.fn() }) }));
vi.mock('../api/usePtzMove', () => ({
  usePtzMove: () => ({ mutate: vi.fn(), isPending: false }),
}));
vi.mock('./LiveFrame', () => ({
  LiveFrame: ({ cameraName }: { cameraName: string }) => <div>Preview for {cameraName}</div>,
}));

describe('LiveFeedingPage', () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockReturnValue({
      principal: { id: 'reviewer', fullName: 'Reviewer', roles: ['reviewer'] },
    } as never);
  });

  it('shows queue depth and the latest camera detection state', () => {
    vi.mocked(useQueueQuery).mockReturnValue({
      data: {
        pages: [
          {
            ...makeQueuePage([], 7),
            why_not_review: [
              {
                camera_id: 'camera-1',
                camera_name: 'Fifth floor',
                stream: 'online',
                last_seen_classes: ['person', 'cell phone'],
                watched_classes: ['bottle', 'cell phone'],
                why_not_review: ['cell phone confidence 0.43 < threshold 0.50'],
                matched: false,
                observed_at: '2026-08-20T12:00:00Z',
              },
            ],
          },
        ],
        pageParams: [undefined],
      },
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<LiveFeedingPage />);

    expect(screen.getByText('Queue depth: 7')).toBeInTheDocument();
    expect(screen.getByText('Fifth floor')).toBeInTheDocument();
    expect(screen.getByText('Camera online')).toBeInTheDocument();
    expect(screen.getByText('Scanning')).toBeInTheDocument();
    expect(screen.getByText('person, cell phone')).toBeInTheDocument();
    expect(screen.getByText('bottle, cell phone')).toBeInTheDocument();
    expect(screen.getByText(/confidence 0.43 < threshold 0.50/)).toBeInTheDocument();
    expect(screen.getByText('Preview for Fifth floor')).toBeInTheDocument();
  });

  it('shows directional PTZ controls to a site administrator', () => {
    vi.mocked(useAuth).mockReturnValue({
      principal: { id: 'admin', fullName: 'Admin', roles: ['site_admin'] },
    } as never);
    vi.mocked(useQueueQuery).mockReturnValue({
      data: {
        pages: [
          {
            ...makeQueuePage([], 0),
            why_not_review: [
              {
                camera_id: 'camera-1',
                camera_name: 'Fifth floor',
                stream: 'online',
                last_seen_classes: [],
                watched_classes: [],
                why_not_review: [],
                matched: false,
                observed_at: '2026-08-20T12:00:00Z',
              },
            ],
          },
        ],
        pageParams: [undefined],
      },
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<LiveFeedingPage />);

    expect(screen.getByRole('button', { name: 'Move Fifth floor up' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Move Fifth floor down' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Move Fifth floor left' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Move Fifth floor right' })).toBeEnabled();
  });
});
