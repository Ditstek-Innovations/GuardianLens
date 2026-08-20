import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { makeQueueEvent, makeQueuePage } from '@/test/factories';

import { useDecidedEvents } from '../api/useDecidedEvents';
import { DecisionDrilldown } from './DecisionDrilldown';

vi.mock('../api/useDecidedEvents', () => ({ useDecidedEvents: vi.fn() }));

const result = (items: ReturnType<typeof makeQueueEvent>[], total: number) => ({
  data: { pages: [makeQueuePage(items, total)], pageParams: [undefined] },
  isPending: false,
  isError: false,
  refetch: vi.fn(),
  hasNextPage: false,
  fetchNextPage: vi.fn(),
  isFetchingNextPage: false,
});

describe('DecisionDrilldown', () => {
  it('shows full totals but renders ten records per independent page', async () => {
    const accepted = Array.from({ length: 200 }, (_, index) =>
      makeQueueEvent({ id: `accepted-${index}`, status: 'accepted' }),
    );
    const corrected = Array.from({ length: 2 }, (_, index) =>
      makeQueueEvent({ id: `corrected-${index}`, status: 'corrected' }),
    );
    const rejected = Array.from({ length: 15 }, (_, index) =>
      makeQueueEvent({ id: `rejected-${index}`, status: 'rejected' }),
    );
    vi.mocked(useDecidedEvents).mockImplementation((_params, status) => {
      if (status === 'accepted') return result(accepted, 200) as never;
      if (status === 'corrected') return result(corrected, 2) as never;
      return result(rejected, 15) as never;
    });

    render(
      <MemoryRouter>
        <DecisionDrilldown
          params={{
            from: '2026-08-01T00:00:00Z',
            to: '2026-08-20T23:59:59Z',
            groupBy: 'zone',
            siteId: null,
          }}
        />
      </MemoryRouter>,
    );

    const passed = screen.getByRole('region', { name: 'Verified records of the period' });
    const failed = screen.getByRole('region', { name: 'Rejected candidates of the period' });
    expect(within(passed).getByText(/verified records \(202\)/i)).toBeInTheDocument();
    expect(within(passed).getAllByRole('link')).toHaveLength(10);
    expect(within(failed).getAllByRole('link')).toHaveLength(10);
    expect(within(passed).getByText('Page 1 of 21 · 202 records')).toBeInTheDocument();
    expect(within(failed).getByText('Page 1 of 2 · 15 records')).toBeInTheDocument();

    await userEvent.click(within(passed).getByRole('button', { name: 'Next' }));
    expect(within(passed).getByText('Page 2 of 21 · 202 records')).toBeInTheDocument();
    expect(within(failed).getByText('Page 1 of 2 · 15 records')).toBeInTheDocument();
  });
});
