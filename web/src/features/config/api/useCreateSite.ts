import { useMutation, useQueryClient } from '@tanstack/react-query';

import { apiClient } from '@/lib/api/client';

import { configKeys } from './configKeys';

import type { Site } from '@/lib/api/types';

export interface CreateSiteInput {
  readonly name: string;
  /** IANA zone, e.g. "Asia/Kolkata" — timestamps render in site-local time. */
  readonly timezone: string;
}

/**
 * POST /sites — creates the site AND grants the creator site_admin there in
 * one audited transaction (a site manageable by no one would be an orphan
 * by construction).
 */
export const useCreateSite = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateSiteInput) =>
      apiClient.post<Site>('/api/v1/sites', {
        name: input.name,
        timezone: input.timezone,
      }),
    onSettled: () => {
      // CS-D-05 — invalidate precisely.
      void queryClient.invalidateQueries({ queryKey: configKeys.sites() });
    },
  });
};
