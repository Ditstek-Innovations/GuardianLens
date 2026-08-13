import { useMutation, useQueryClient } from '@tanstack/react-query';

import { apiClient } from '@/lib/api/client';

import { configKeys } from './configKeys';

import type { ZoneSummary } from '@/lib/api/types';

export interface CreateZoneInput {
  readonly cameraId: string;
  readonly name: string;
  /** Normalised 0–1 vertex space (TRD §10.6) — survives a resolution change. */
  readonly polygon: readonly (readonly [number, number])[];
}

export const useCreateZone = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateZoneInput) =>
      apiClient.post<ZoneSummary>('/api/v1/zones', {
        camera_id: input.cameraId,
        name: input.name,
        polygon: input.polygon.map((vertex) => [...vertex]),
      }),
    onSettled: () => {
      // CS-D-05 — invalidate precisely.
      void queryClient.invalidateQueries({ queryKey: configKeys.zones() });
    },
  });
};
