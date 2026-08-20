import { useQuery } from '@tanstack/react-query';

import { apiClient } from '@/lib/api/client';

import { eventKeys } from './eventKeys';

import type { CorrectionOptions } from '@/lib/api/types';

export const useCorrectionOptions = (eventId: string, enabled: boolean) =>
  useQuery({
    queryKey: eventKeys.correctionOptions(eventId),
    queryFn: ({ signal }) =>
      apiClient.get<CorrectionOptions>(`/api/v1/events/${eventId}/correction-options`, { signal }),
    enabled: enabled && eventId !== '',
  });

