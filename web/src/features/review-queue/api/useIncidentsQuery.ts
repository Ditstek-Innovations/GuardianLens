import { useQuery } from '@tanstack/react-query';

import { EVENT_STATUS } from '@/constants/events';
import { QUEUE_POLL_INTERVAL_MS, QUEUE_STALE_TIME_MS } from '@/constants/query';
import { apiClient } from '@/lib/api/client';

import { queueKeys } from './queryKeys';

import type { IncidentQueueResponse } from '@/lib/api/types';

/**
 * The queue grouped into incidents — same polling posture as the flat
 * queue (TRD §7.3). Grouping is display-level; decisions stay one-by-one
 * through the ordinary event routes (BR-V-02).
 */
export const useIncidentsQuery = () =>
  useQuery({
    queryKey: queueKeys.incidents(EVENT_STATUS.UNVERIFIED),
    queryFn: ({ signal }) =>
      apiClient.get<IncidentQueueResponse>('/api/v1/events/incidents', {
        query: { status: EVENT_STATUS.UNVERIFIED },
        signal,
      }),
    staleTime: QUEUE_STALE_TIME_MS,
    refetchInterval: QUEUE_POLL_INTERVAL_MS,
    // CS-P-07 — polling pauses when the document is hidden.
    refetchIntervalInBackground: false,
  });
