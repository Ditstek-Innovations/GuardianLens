import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { useQueueQuery } from '@/features/review-queue';
import { makeQueuePage } from '@/test/factories';

import { LiveFeedingPage } from './LiveFeedingPage';

vi.mock('@/features/review-queue', () => ({ useQueueQuery: vi.fn() }));
vi.mock('./LiveFrame', () => ({
  LiveFrame: ({ cameraName }: { cameraName: string }) => <div>Preview for {cameraName}</div>,
}));

describe('LiveFeedingPage', () => {
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
});
