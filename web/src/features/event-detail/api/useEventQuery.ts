import { useQuery } from '@tanstack/react-query';

import { apiClient } from '@/lib/api/client';
import { AUTO_REFRESH_INTERVAL_MS } from '@/constants/query';

import { eventKeys } from './eventKeys';

import type { EventDetail } from '@/lib/api/types';

export const useEventQuery = (eventId: string) =>
  useQuery({
    queryKey: eventKeys.detail(eventId),
    queryFn: ({ signal }) => apiClient.get<EventDetail>(`/api/v1/events/${eventId}`, { signal }),
    enabled: eventId !== '',
    refetchInterval: AUTO_REFRESH_INTERVAL_MS,
  });
