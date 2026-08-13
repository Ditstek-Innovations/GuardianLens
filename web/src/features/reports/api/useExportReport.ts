import { useMutation } from '@tanstack/react-query';

import { apiClient } from '@/lib/api/client';

import type { ReportParams } from '../types';

/**
 * GET /api/v1/reports/export — CSV with a provenance header (BR-R-02).
 * ASSUMPTION A-12 — export accepts the same query parameters as summary plus
 * `format=csv`; the TRD names the endpoint without listing its parameters.
 */
export const useExportReport = () =>
  useMutation({
    mutationFn: (params: ReportParams) =>
      apiClient.getBlob('/api/v1/reports/export', {
        query: {
          format: 'csv',
          from: params.from,
          to: params.to,
          group_by: params.groupBy,
          ...(params.siteId !== null ? { site_id: params.siteId } : {}),
        },
      }),
  });
