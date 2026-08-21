import { useInfiniteQuery } from '@tanstack/react-query';

import { apiClient } from '@/lib/api/client';
import { AUTO_REFRESH_INTERVAL_MS } from '@/constants/query';

import { reportKeys } from './reportKeys';

import type { QueuePage } from '@/lib/api/types';
import type { ReportParams } from '../types';

const PAGE_LIMIT = 200;

/**
 * Decided events of the report period, one status per call — the
 * drill-down behind the analytics tiles. BR-007: rejected candidates are
 * retained and VISIBLE; this is where a customer sees each one.
 */
export const useDecidedEvents = (params: ReportParams, status: string) =>
  useInfiniteQuery({
    queryKey: [...reportKeys.all, 'decided', status, params] as const,
    queryFn: ({ pageParam, signal }) =>
      apiClient.get<QueuePage>('/api/v1/events', {
        query: {
          status,
          from: params.from,
          to: params.to,
          limit: PAGE_LIMIT,
          ...(pageParam !== undefined ? { cursor: pageParam } : {}),
          ...(params.siteId !== null ? { site_id: params.siteId } : {}),
        },
        signal,
      }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    enabled: params.from !== '' && params.to !== '',
    refetchInterval: AUTO_REFRESH_INTERVAL_MS,
  });
