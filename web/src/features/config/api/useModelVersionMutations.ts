import { useMutation, useQueryClient } from '@tanstack/react-query';

import { apiClient } from '@/lib/api/client';

import { configKeys } from './configKeys';

import type { ModelVersionSummary } from '@/lib/api/types';

export interface RegisterModelVersionInput {
  readonly version: string;
  readonly artefactHash: string;
  readonly classes: readonly string[];
  readonly modelCardRef: string;
  readonly datasheetRef: string;
  readonly notes: string | null;
}

/**
 * POST /model-versions. Registration is the G1 evidence trail — it is not
 * approval and not deployment (chk_model_deployed_requires_approval).
 */
export const useRegisterModelVersion = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: RegisterModelVersionInput) =>
      apiClient.post<ModelVersionSummary>('/api/v1/model-versions', {
        version: input.version,
        artefact_hash: input.artefactHash,
        classes: input.classes,
        model_card_ref: input.modelCardRef,
        datasheet_ref: input.datasheetRef,
        notes: input.notes,
      }),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: configKeys.models() });
    },
  });
};

/**
 * POST /model-versions/{id}/approve. Approver comes from the token; the
 * request carries no body (BR-C-02 applied to gate G1).
 */
export const useApproveModelVersion = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (modelVersionId: string) =>
      apiClient.post<ModelVersionSummary>(`/api/v1/model-versions/${modelVersionId}/approve`),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: configKeys.models() });
    },
  });
};
