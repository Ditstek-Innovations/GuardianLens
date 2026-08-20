import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { makeQueueEvent, makeQueuePage } from '@/test/factories';

import { useHistoryQuery } from '../api/useHistoryQuery';
import { HistoryPage } from './HistoryPage';

vi.mock('../api/useHistoryQuery', () => ({ useHistoryQuery: vi.fn() }));
vi.mock('./EvidenceThumb', () => ({
  EvidenceThumb: () => <span>Frame</span>,
}));

describe('HistoryPage', () => {
  it('renders ten records per page and fetches another cursor only when needed', async () => {
    const events = Array.from({ length: 25 }, (_, index) =>
      makeQueueEvent({
        id: `accepted-${index}`,
        status: 'accepted',
        rule: { human_readable: `Accepted record ${index + 1}` },
      }),
    );
    const fetchNextPage = vi.fn().mockResolvedValue(undefined);
    vi.mocked(useHistoryQuery).mockReturnValue({
      data: {
        pages: [makeQueuePage(events, 35, 'next-cursor')],
        pageParams: [undefined],
      },
      isPending: false,
      isError: false,
      refetch: vi.fn(),
      hasNextPage: true,
      fetchNextPage,
      isFetchingNextPage: false,
    } as never);

    render(
      <MemoryRouter initialEntries={['/history?status=accepted']}>
        <HistoryPage />
      </MemoryRouter>,
    );

    expect(screen.getByText('Page 1 of 4 · 35 records')).toBeInTheDocument();
    expect(screen.getByText('Accepted record 1')).toBeInTheDocument();
    expect(screen.queryByText('Accepted record 11')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Next' }));
    expect(screen.getByText('Page 2 of 4 · 35 records')).toBeInTheDocument();
    expect(screen.getByText('Accepted record 11')).toBeInTheDocument();
    expect(fetchNextPage).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole('button', { name: 'Next' }));
    expect(screen.getByText('Page 3 of 4 · 35 records')).toBeInTheDocument();
    expect(screen.getByText('Accepted record 21')).toBeInTheDocument();
    expect(fetchNextPage).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getByRole('button', { name: 'Previous' }));
    expect(screen.getByText('Page 2 of 4 · 35 records')).toBeInTheDocument();
  });

  it('reads date-and-time filters from the URL and sends ISO timestamps to the API', async () => {
    vi.mocked(useHistoryQuery).mockReturnValue({
      data: { pages: [makeQueuePage([], 0)], pageParams: [undefined] },
      isPending: false,
      isError: false,
      refetch: vi.fn(),
      hasNextPage: false,
      fetchNextPage: vi.fn(),
      isFetchingNextPage: false,
    } as never);
    const from = '2026-08-20T09:30';
    const to = '2026-08-20T17:45';

    render(
      <MemoryRouter initialEntries={[`/history?status=accepted&from=${from}&to=${to}`]}>
        <HistoryPage />
      </MemoryRouter>,
    );

    expect(screen.getByLabelText('From date and time')).toHaveValue(from);
    expect(screen.getByLabelText('To date and time')).toHaveValue(to);
    expect(useHistoryQuery).toHaveBeenLastCalledWith(
      'accepted',
      new Date(from).toISOString(),
      new Date(to).toISOString(),
    );

    const changedFrom = '2026-08-20T10:15';
    fireEvent.change(screen.getByLabelText('From date and time'), {
      target: { value: changedFrom },
    });
    expect(useHistoryQuery).toHaveBeenLastCalledWith(
      'accepted',
      new Date(changedFrom).toISOString(),
      new Date(to).toISOString(),
    );

    await userEvent.click(screen.getByRole('button', { name: 'Clear dates' }));
    expect(screen.getByLabelText('From date and time')).toHaveValue('');
    expect(screen.getByLabelText('To date and time')).toHaveValue('');
    expect(useHistoryQuery).toHaveBeenLastCalledWith('accepted', undefined, undefined);
  });
});
