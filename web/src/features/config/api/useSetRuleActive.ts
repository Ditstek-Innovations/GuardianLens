import { useMutation, useQueryClient } from '@tanstack/react-query';

import { apiClient } from '@/lib/api/client';

import { configKeys } from './configKeys';

export interface SetRuleActiveInput {
  readonly ruleId: string;
  readonly isActive: boolean;
}

/**
 * BR-001 — activation is an explicit act: POST /rules/{id}/activate
 * (TRD §10.6). ASSUMPTION A-11 — deactivation goes through
 * PATCH /rules/{id} { is_active: false } as shown in ARCHITECTURE RS-4;
 * the TRD names no dedicated deactivate route.
 */
export const useSetRuleActive = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ ruleId, isActive }: SetRuleActiveInput) =>
      isActive
        ? apiClient.post<unknown>(`/api/v1/rules/${ruleId}/activate`)
        : apiClient.patch<unknown>(`/api/v1/rules/${ruleId}`, { is_active: false }),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: configKeys.rules() });
    },
  });
};
