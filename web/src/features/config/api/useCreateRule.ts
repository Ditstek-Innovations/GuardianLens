import { useMutation, useQueryClient } from '@tanstack/react-query';

import { apiClient } from '@/lib/api/client';

import { configKeys } from './configKeys';

import type { RuleSummary } from '@/lib/api/types';

export interface CreateRuleInput {
  readonly zoneId: string;
  readonly ruleType: string;
  readonly confidenceThreshold: number;
  readonly debounceSeconds: number;
  readonly humanReadable: string;
  readonly writtenRuleReference: string | null;
}

/**
 * POST /rules — the rule is created INACTIVE, always (BR-001): the schema
 * carries no is_active field and the server refuses one. Activation is the
 * separate, confirmed, attributed act (BR-C-02).
 */
export const useCreateRule = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateRuleInput) =>
      apiClient.post<RuleSummary>('/api/v1/rules', {
        zone_id: input.zoneId,
        rule_type: input.ruleType,
        confidence_threshold: input.confidenceThreshold,
        debounce_seconds: input.debounceSeconds,
        human_readable: input.humanReadable,
        written_rule_reference: input.writtenRuleReference,
      }),
    onSettled: () => {
      // CS-D-05 — invalidate precisely.
      void queryClient.invalidateQueries({ queryKey: configKeys.rules() });
    },
  });
};
