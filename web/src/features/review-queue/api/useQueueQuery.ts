import { useInfiniteQuery } from '@tanstack/react-query';

import { EVENT_STATUS } from '@/constants/events';
import { QUEUE_PAGE_SIZE, QUEUE_POLL_INTERVAL_MS, QUEUE_STALE_TIME_MS } from '@/constants/query';
import { apiClient } from '@/lib/api/client';

import { queueKeys } from './queryKeys';

import type { QueueEventItem, QueuePage } from '@/lib/api/types';

/**
 * TRD §7.3 — the queue polls every 15 s [MVP]; TRD §10.1 — cursor pagination,
 * never page numbers. All server state via TanStack Query (CS-D-01).
 */
export const useQueueQuery = () =>
  useInfiniteQuery({
    queryKey: queueKeys.list(EVENT_STATUS.UNVERIFIED),
    queryFn: ({ pageParam, signal }) =>
      apiClient.get<QueuePage>('/api/v1/events', {
        query: {
          status: EVENT_STATUS.UNVERIFIED,
          limit: QUEUE_PAGE_SIZE,
          ...(pageParam !== undefined ? { cursor: pageParam } : {}),
        },
        signal,
      }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    staleTime: QUEUE_STALE_TIME_MS,
    refetchInterval: QUEUE_POLL_INTERVAL_MS,
    // CS-P-07 — polling pauses when the document is hidden.
    refetchIntervalInBackground: false,
  });

export const flattenQueueItems = (pages: readonly QueuePage[]): QueueEventItem[] =>
  pages.flatMap((page) => page.items);
