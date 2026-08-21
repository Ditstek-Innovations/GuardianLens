import { useMutation, useQueryClient } from "@tanstack/react-query";

import { queueKeys } from "@/features/review-queue";
import { apiClient } from "@/lib/api/client";
import { assertNever } from "@/lib/utils/assertNever";

import type { InfiniteData } from "@tanstack/react-query";
import type {
  DecisionRequestBody,
  DecisionResponse,
  QueuePage,
} from "@/lib/api/types";
import type { Decision } from "@/types/decision";

/**
 * BR-S-01 / CS-B-05 — reviewer identity comes from the session token only.
 * No request variant carries reviewer_id; the type makes that unrepresentable.
 */
const toRequestBody = (
  decision: Decision,
  version: number,
): DecisionRequestBody => {
  switch (decision.type) {
    case "accept":
      return { decision: "accept", version };
    case "reject":
      return {
        decision: "reject",
        rejection_reason: decision.reason,
        training_feedback: "false_positive",
        version,
      };
    case "correct":
      return {
        decision: "correct",
        corrections: [
          {
            field: decision.correction.field,
            value: decision.correction.value,
          },
        ],
        version,
      };
    default:
      return assertNever(decision);
  }
};

type QueueData = InfiniteData<QueuePage, string | undefined>;

const removeFromQueue =
  (eventId: string) =>
  (data: QueueData | undefined): QueueData | undefined => {
    if (data === undefined) return undefined;
    return {
      ...data,
      pages: data.pages.map((page) => ({
        ...page,
        items: page.items.filter((item) => item.id !== eventId),
        queue_depth: Math.max(page.queue_depth - 1, 0),
      })),
    };
  };

export interface SubmitDecisionInput {
  readonly decision: Decision;
  readonly version: number;
}

export const useSubmitDecision = (eventId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ decision, version }: SubmitDecisionInput) =>
      apiClient.post<DecisionResponse>(
        `/api/v1/events/${eventId}/decision`,
        toRequestBody(decision, version),
      ),

    // The optimistic scope is deliberately narrow (CS-D-06): the candidate
    // leaves the queue so the reviewer moves on immediately. Nothing is ever
    // optimistically rendered as a verified record, count or report entry —
    // until the server confirms, no Verified Record exists (BR-004, CS-B-06).
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: queueKeys.lists() });
      const previous = queryClient.getQueriesData<QueueData>({
        queryKey: queueKeys.lists(),
      });
      queryClient.setQueriesData<QueueData>(
        { queryKey: queueKeys.lists() },
        removeFromQueue(eventId),
      );
      return { previous };
    },

    onError: (_error, _input, context) => {
      // Rollback is mandatory — CS-D-06 / CS-Q-11. A decision that appears to
      // have succeeded when it did not is a BR-004 integrity failure.
      context?.previous.forEach(([queryKey, data]) => {
        queryClient.setQueryData(queryKey, data);
      });
    },

    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queueKeys.all });
    },
  });
};
