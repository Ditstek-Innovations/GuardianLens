import { useMutation, useQueryClient } from '@tanstack/react-query';

import { EVENT_STATUS } from '@/constants/events';
import { apiClient } from '@/lib/api/client';

import { queueKeys } from './queryKeys';

import type {
  DecisionRequestBody,
  DecisionResponse,
  QueueEventItem,
  QueuePage,
} from '@/lib/api/types';

const BULK_FETCH_SIZE = 100;
const DECISION_BATCH_SIZE = 5;

export interface AcceptAllResult {
  readonly accepted: number;
  readonly failed: number;
}

const loadAllPending = async (): Promise<QueueEventItem[]> => {
  const items: QueueEventItem[] = [];
  let cursor: string | undefined;

  do {
    const page = await apiClient.get<QueuePage>('/api/v1/events', {
      query: {
        status: EVENT_STATUS.UNVERIFIED,
        limit: BULK_FETCH_SIZE,
        ...(cursor !== undefined ? { cursor } : {}),
      },
    });
    items.push(...page.items);
    cursor = page.next_cursor ?? undefined;
  } while (cursor !== undefined);

  return items;
};

const acceptPending = async (): Promise<AcceptAllResult> => {
  const items = await loadAllPending();
  let accepted = 0;
  let failed = 0;

  // Keep every acceptance as its own version-checked, audited decision while
  // limiting concurrency so a large queue cannot overwhelm the API.
  for (let start = 0; start < items.length; start += DECISION_BATCH_SIZE) {
    const batch = items.slice(start, start + DECISION_BATCH_SIZE);
    const outcomes = await Promise.allSettled(
      batch.map((item) => {
        const body: DecisionRequestBody = { decision: 'accept', version: item.version };
        return apiClient.post<DecisionResponse>(`/api/v1/events/${item.id}/decision`, body);
      }),
    );
    accepted += outcomes.filter((outcome) => outcome.status === 'fulfilled').length;
    failed += outcomes.filter((outcome) => outcome.status === 'rejected').length;
  }

  return { accepted, failed };
};

export const useAcceptAllQueue = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: acceptPending,
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queueKeys.all });
    },
  });
};
