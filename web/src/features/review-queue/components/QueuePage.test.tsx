import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ToastProvider } from '@/components/ui';
import { AuthContext } from '@/hooks/useAuth';
import {
  jsonResponse,
  makeIncidentGroup,
  makeIncidentsResponse,
  makeQueueEvent,
  makeQueuePage,
} from '@/test/factories';

import { QueuePage } from './QueuePage';

import type { IncidentQueueResponse, QueuePage as QueuePageBody } from '@/lib/api/types';

/** URL-aware stub: the page talks to both the flat and the grouped queue. */
const stubQueueApi = (flat: QueuePageBody, incidents: IncidentQueueResponse): void => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes('/events/incidents')) return jsonResponse(incidents);
      return jsonResponse(flat);
    }),
  );
};

const renderQueuePage = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    // A reviewer principal: the page renders; the site-admin AI-review
    // toggle stays absent for this role (absent, not disabled).
    <AuthContext.Provider
      value={{
        principal: { id: 'user-1', fullName: 'A. Reviewer', roles: ['reviewer'] },
        restoring: false,
        signIn: async () => undefined,
        signOut: () => undefined,
      }}
    >
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <MemoryRouter>
            <QueuePage />
          </MemoryRouter>
        </ToastProvider>
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('QueuePage', () => {
  it('defaults to grouped incidents: one row per ongoing condition, count visible, no bulk affordance', async () => {
    stubQueueApi(
      makeQueuePage([makeQueueEvent()], 4),
      makeIncidentsResponse([
        makeIncidentGroup(),
        makeIncidentGroup({
          incident_key: 'event-9',
          rule: { human_readable: 'No entry while forklift active' },
          count: 1,
          event_ids: ['event-9'],
        }),
      ]),
    );

    renderQueuePage();

    expect(await screen.findByText('Helmet required in Bay 3')).toBeInTheDocument();
    expect(screen.getByText('No entry while forklift active')).toBeInTheDocument();
    // The group carries its member count as information…
    expect(screen.getByText(/3 candidates/i)).toBeInTheDocument();
    // …and depth stays visible (DP-4).
    expect(screen.getByText(/queue depth: 4/i)).toBeInTheDocument();
    // BR-V-02 — grouping adds no bulk decision affordance.
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /accept all/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /decide all/i })).not.toBeInTheDocument();
  });

  it('switches to the flat view with camera, zone, rule and status chips, still without bulk affordances', async () => {
    stubQueueApi(
      makeQueuePage(
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
      ),
      makeIncidentsResponse([makeIncidentGroup()]),
    );

    renderQueuePage();
    await screen.findByText('Helmet required in Bay 3');
    await userEvent.click(screen.getByRole('button', { name: /all candidates/i }));

    expect(await screen.findByText('No entry while forklift active')).toBeInTheDocument();
    expect(screen.getByText(/bay 3 entrance · bay 3 ppe area/i)).toBeInTheDocument();
    expect(screen.getByText(/queue depth: 7/i)).toBeInTheDocument();
    // Status chips carry text, never colour alone — NFR-ACC-02.
    expect(screen.getAllByText('Unverified')).toHaveLength(2);
    // Absent, not disabled (BR-V-02, CS-Q-10).
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
    expect(screen.queryByText(/select all/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /bulk/i })).not.toBeInTheDocument();
  });

  it('keeps the queue depth visible when the queue is empty', async () => {
    stubQueueApi(makeQueuePage([], 0), makeIncidentsResponse([]));

    renderQueuePage();

    expect(await screen.findByText(/queue clear/i)).toBeInTheDocument();
    expect(screen.getByText(/queue depth: 0/i)).toBeInTheDocument();
  });

  it('shows why Review is empty from the latest edge snapshot', async () => {
    stubQueueApi(
      makeQueuePage([], 0),
      makeIncidentsResponse([], 0, [
        {
          camera_id: 'camera-1',
          camera_name: 'Bay 3 entrance',
          stream: 'online',
          last_seen_classes: ['person', 'chair'],
          watched_classes: ['cell phone'],
          why_not_review: [
            "rule 'Mobile uses' watches 'cell phone'; frame classes: person, chair",
          ],
          matched: false,
        },
      ]),
    );

    renderQueuePage();

    expect(await screen.findByText('Why Review is empty')).toBeInTheDocument();
    expect(screen.getByText('Bay 3 entrance')).toBeInTheDocument();
    expect(screen.getByText(/watches 'cell phone'/)).toBeInTheDocument();
    expect(screen.getByText(/YOLO last saw: person, chair/)).toBeInTheDocument();
  });
});
