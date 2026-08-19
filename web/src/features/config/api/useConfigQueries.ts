import { useQuery } from '@tanstack/react-query';

import { apiClient } from '@/lib/api/client';
import { unwrapItems } from '@/lib/api/list';

import { configKeys } from './configKeys';

import type {
  CameraSummary,
  ListResponse,
  ModelVersionSummary,
  RuleSummary,
  Site,
  ZoneSummary,
} from '@/lib/api/types';

/** TRD §10.6 — GET /sites is site_admin scoped, so callers gate `enabled`. */
export const useSitesQuery = (enabled: boolean) =>
  useQuery({
    queryKey: configKeys.sites(),
    queryFn: async ({ signal }) =>
      unwrapItems(await apiClient.get<ListResponse<Site> | Site[]>('/api/v1/sites', { signal })),
    enabled,
  });

/** TRD §10.6 — GET /cameras is site_admin scoped too; non-admin callers gate `enabled`. */
export const useCamerasQuery = (enabled: boolean = true) =>
  useQuery({
    queryKey: configKeys.cameras(),
    queryFn: async ({ signal }) =>
      unwrapItems(
        await apiClient.get<ListResponse<CameraSummary> | CameraSummary[]>('/api/v1/cameras', {
          signal,
        }),
      ),
    enabled,
  });

export const useZonesQuery = () =>
  useQuery({
    queryKey: configKeys.zones(),
    queryFn: async ({ signal }) =>
      unwrapItems(
        await apiClient.get<ListResponse<ZoneSummary> | ZoneSummary[]>('/api/v1/zones', { signal }),
      ),
  });

export const useRulesQuery = () =>
  useQuery({
    queryKey: configKeys.rules(),
    queryFn: async ({ signal }) =>
      unwrapItems(
        await apiClient.get<ListResponse<RuleSummary> | RuleSummary[]>('/api/v1/rules', { signal }),
      ),
  });

const fetchModelVersions = async (signal?: AbortSignal): Promise<ModelVersionSummary[]> =>
  unwrapItems(
    await apiClient.get<ListResponse<ModelVersionSummary> | ModelVersionSummary[]>(
      '/api/v1/model-versions',
      { signal },
    ),
  );

/** JSONB classes should be a string list; tolerate a malformed row so the table still renders. */
export const modelClassNames = (classes: unknown): string[] =>
  Array.isArray(classes)
    ? classes.filter((value): value is string => typeof value === 'string' && value.trim() !== '')
    : [];

/** TRD §10.6 — GET /model-versions is site_admin scoped. */
export const useModelVersionsQuery = () =>
  useQuery({
    queryKey: configKeys.models(),
    queryFn: async ({ signal }) => fetchModelVersions(signal),
  });

/**
 * Derives the live list of detectable class names from all registered model
 * versions. Deduplicated and sorted so the rule form always reflects the
 * current model manifest — no manual maintenance required.
 */
export const useModelClassesQuery = () =>
  useQuery({
    queryKey: configKeys.models(),
    queryFn: async ({ signal }) => fetchModelVersions(signal),
    select: (models) => [...new Set(models.flatMap((model) => modelClassNames(model.classes)))].sort(),
  });
