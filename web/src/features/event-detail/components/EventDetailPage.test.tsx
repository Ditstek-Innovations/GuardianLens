// §12.2 — the decision flow surfaces catalogue copy through the toast
// channel: an accept states the attribution (BR-005), a reject states the
// retention (BR-007). Asserts the EXACT shipped strings (CS-MSG-02/04).
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ToastProvider } from '@/components/ui';
import { MESSAGES } from '@/constants/messages';
import { AuthContext } from '@/hooks/useAuth';
import { jsonResponse, makeQueueEvent, makeQueuePage } from '@/test/factories';

import { EventDetailPage } from './EventDetailPage';

import type { EventDetail } from '@/lib/api/types';

const makeEventDetail = (): EventDetail => ({
  ...makeQueueEvent(),
  rule_snapshot: {
    rule_type: 'ppe_helmet',
    confidence_threshold: 1,
    human_readable: 'Helmet required in Bay 3',
    debounce_seconds: 30,
    dwell_seconds: null,
    detection_class: 'person_without_helmet',
  },
});

const stubApi = (): void => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes('/evidence')) {
        return new Response(new Blob(['frame']), {
          status: 200,
          headers: { 'Content-Type': 'image/jpeg' },
        });
      }
      if (url.includes('/decision') && init?.method === 'POST') {
        return jsonResponse({ decision_type: 'accept' });
      }
      if (url.includes('/events/event-1')) return jsonResponse(makeEventDetail());
      // Queue list (shared cache for next-candidate computation).
      return jsonResponse(makeQueuePage([], 0));
    }),
  );
};

const renderDetail = () => {
  // jsdom has no object-URL implementation; the evidence hook needs one.
  vi.stubGlobal('URL', Object.assign(URL, {
    createObjectURL: vi.fn(() => 'blob:evidence'),
    revokeObjectURL: vi.fn(),
  }));
  stubApi();
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
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
          <MemoryRouter initialEntries={['/queue/event-1']}>
            <Routes>
              <Route path="/queue/:eventId" element={<EventDetailPage />} />
              <Route path="/queue" element={<p>queue home</p>} />
            </Routes>
          </MemoryRouter>
        </ToastProvider>
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
};

const loadEvidence = async (): Promise<void> => {
  const frame = await screen.findByAltText(/evidence frame/i);
  fireEvent.load(frame);
};

afterEach(() => {
  vi.unstubAllGlobals();
  sessionStorage.clear();
});

describe('EventDetailPage decision outcomes', () => {
  it('accept renders the exact catalogue message (BR-005, CS-MSG-04)', async () => {
    const user = userEvent.setup();
    renderDetail();
    await loadEvidence();

    await user.click(await screen.findByRole('button', { name: /accept/i }));

    const toast = await screen.findByRole('status');
    expect(toast).toHaveTextContent(MESSAGES.decision.accepted);
    expect(toast).toHaveTextContent('Recorded as a verified event — it now carries your name.');
  });

  it('reject renders the exact catalogue message (BR-007, CS-MSG-04)', async () => {
    const user = userEvent.setup();
    renderDetail();
    await loadEvidence();

    await user.click(await screen.findByRole('button', { name: 'Reject R' }));
    await user.type(await screen.findByLabelText(/rejection reason/i), 'No person in frame');
    await user.click(screen.getByRole('button', { name: /reject candidate/i }));

    const toast = await screen.findByRole('status');
    expect(toast).toHaveTextContent(MESSAGES.decision.rejected);
    expect(toast).toHaveTextContent('Recorded as rejected — it stays visible in the rejection log.');
  });
});
