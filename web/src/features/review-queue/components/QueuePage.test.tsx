import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { jsonResponse, makeQueueEvent, makeQueuePage } from '@/test/factories';

import { QueuePage } from './QueuePage';

const renderQueuePage = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <QueuePage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('QueuePage', () => {
  it('renders queue rows from the API with camera, zone, rule, time and status chip', async () => {
    const page = makeQueuePage(
      [
        makeQueueEvent(),
        makeQueueEvent({
          id: 'event-2',
          camera: { id: 'camera-2', name: 'Dock west' },
          zone: { id: 'zone-2', name: 'Forklift lane' },
          rule: { human_readable: 'No entry while forklift active' },
        }),
      ],
      7,
    );
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(page)));

    renderQueuePage();

    expect(await screen.findByText('Helmet required in Bay 3')).toBeInTheDocument();
    expect(screen.getByText('No entry while forklift active')).toBeInTheDocument();
    expect(screen.getByText(/bay 3 entrance · bay 3 ppe area/i)).toBeInTheDocument();
    // Queue depth always visible — DP-4.
    expect(screen.getByText(/queue depth: 7/i)).toBeInTheDocument();
    // Status chips carry text, never colour alone — NFR-ACC-02.
    expect(screen.getAllByText('Unverified')).toHaveLength(2);
  });

  it('contains no bulk affordances: no checkboxes, no select-all, no bulk buttons (BR-V-02, CS-Q-10)', async () => {
    const page = makeQueuePage([makeQueueEvent()], 1);
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(page)));

    renderQueuePage();
    await screen.findByText('Helmet required in Bay 3');

    // Absent, not disabled.
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
    expect(screen.queryByText(/select all/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /bulk/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /accept all/i })).not.toBeInTheDocument();
  });

  it('keeps the queue depth visible when the queue is empty', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(makeQueuePage([], 0))));

    renderQueuePage();

    expect(await screen.findByText(/queue clear/i)).toBeInTheDocument();
    expect(screen.getByText(/queue depth: 0/i)).toBeInTheDocument();
  });
});
