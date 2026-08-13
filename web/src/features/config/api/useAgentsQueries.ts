import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiClient } from '@/lib/api/client';
import { unwrapItems } from '@/lib/api/list';

import { configKeys } from './configKeys';

import type { AgentRegistered, AgentSummary, ListResponse } from '@/lib/api/types';

/** TRD §10.6 — GET /agents is site_admin scoped, like sites and cameras. */
export const useAgentsQuery = () =>
  useQuery({
    queryKey: configKeys.agents(),
    queryFn: async ({ signal }) =>
      unwrapItems(
        await apiClient.get<ListResponse<AgentSummary> | AgentSummary[]>('/api/v1/agents', {
          signal,
        }),
      ),
  });

export interface RegisterAgentInput {
  readonly siteId: string;
  readonly name: string;
}

/**
 * POST /agents. The response carries the composite credential exactly ONCE
 * (slug:agent_id:secret); the caller shows it and never persists it —
 * not in the cache, not in storage (the CS-AD-06 discipline).
 */
export const useRegisterAgent = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: RegisterAgentInput) =>
      apiClient.post<AgentRegistered>('/api/v1/agents', {
        site_id: input.siteId,
        name: input.name,
      }),
    onSettled: () => {
      // CS-D-05 — invalidate precisely.
      void queryClient.invalidateQueries({ queryKey: configKeys.agents() });
    },
  });
};
