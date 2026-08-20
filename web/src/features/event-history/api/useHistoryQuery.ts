import { useInfiniteQuery } from '@tanstack/react-query';

import { QUEUE_PAGE_SIZE } from '@/constants/query';
import { apiClient } from '@/lib/api/client';

import type { QueuePage } from '@/lib/api/types';

export const historyKeys = {
  all: ['history'] as const,
  list: (status: string, from?: string, to?: string) =>
    [...historyKeys.all, status, from ?? null, to ?? null] as const,
};

/**
 * GET /events with an explicit status filter and cursor pagination —
 * SCR-4's data source. Same wire shape as the queue; no polling: history
 * is a record, not a live surface.
 */
export const useHistoryQuery = (status: string, from?: string, to?: string) =>
  useInfiniteQuery({
    queryKey: historyKeys.list(status, from, to),
    queryFn: ({ pageParam, signal }) =>
      apiClient.get<QueuePage>('/api/v1/events', {
        query: {
          status,
          from,
          to,
          limit: QUEUE_PAGE_SIZE,
          ...(pageParam !== undefined ? { cursor: pageParam } : {}),
        },
        signal,
      }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
  });
