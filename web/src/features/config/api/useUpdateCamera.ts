import { useMutation, useQueryClient } from '@tanstack/react-query';

import { apiClient } from '@/lib/api/client';

import { configKeys } from './configKeys';

import type { CameraSummary } from '@/lib/api/types';

export interface UpdateCameraInput {
  readonly cameraId: string;
  /**
   * WRITE-ONLY replacement (CS-AD-06): sent once, sealed server-side,
   * never echoed. The API records THAT it changed, never what it is.
   */
  readonly streamUrl?: string;
  /** Administrative state only — 'disabled' stops the edge watching it. */
  readonly status?: 'active' | 'disabled';
  readonly streamProfile?: 'primary' | 'secondary';
  readonly sampleRateFps?: number;
}

export const useUpdateCamera = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: UpdateCameraInput) =>
      apiClient.patch<CameraSummary>(`/api/v1/cameras/${input.cameraId}`, {
        ...(input.streamUrl !== undefined ? { stream_url: input.streamUrl } : {}),
        ...(input.status !== undefined ? { status: input.status } : {}),
        ...(input.streamProfile !== undefined ? { stream_profile: input.streamProfile } : {}),
        ...(input.sampleRateFps !== undefined ? { sample_rate_fps: input.sampleRateFps } : {}),
      }),
    onSettled: () => {
      // CS-D-05 — invalidate precisely.
      void queryClient.invalidateQueries({ queryKey: configKeys.cameras() });
    },
  });
};
