import { useMutation, useQueryClient } from '@tanstack/react-query';

import { apiClient } from '@/lib/api/client';

import { configKeys } from './configKeys';

import type { CameraSummary } from '@/lib/api/types';

export interface CreateCameraInput {
  readonly siteId: string;
  readonly name: string;
  /**
   * WRITE-ONLY. The API never returns the stream URL (it is stored encrypted,
   * TRD §12.4/§12.5); after a successful save the UI shows "credential
   * stored" and never re-displays the value.
   */
  readonly streamUrl: string;
  /** Where the camera physically is — real installs need this on the record. */
  readonly locationDescription: string | null;
}

/** ASSUMPTION A-10 — POST /cameras body { site_id, name, stream_url }. */
export const useCreateCamera = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateCameraInput) =>
      apiClient.post<CameraSummary>('/api/v1/cameras', {
        site_id: input.siteId,
        name: input.name,
        stream_url: input.streamUrl,
        location_description: input.locationDescription,
      }),
    onSettled: () => {
      // CS-D-05 — invalidate precisely.
      void queryClient.invalidateQueries({ queryKey: configKeys.cameras() });
    },
  });
};
