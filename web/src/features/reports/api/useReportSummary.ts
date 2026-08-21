import { useQuery } from '@tanstack/react-query';

import { apiClient } from '@/lib/api/client';
import { AUTO_REFRESH_INTERVAL_MS } from '@/constants/query';

import { reportKeys } from './reportKeys';

import type { ReportSummary } from '@/lib/api/types';
import type { ReportParams } from '../types';

export const useReportSummary = (params: ReportParams) =>
  useQuery({
    queryKey: reportKeys.summary(params),
    queryFn: ({ signal }) =>
      apiClient.get<ReportSummary>('/api/v1/reports/summary', {
        query: {
          from: params.from,
          to: params.to,
          group_by: params.groupBy,
          ...(params.siteId !== null ? { site_id: params.siteId } : {}),
        },
        signal,
      }),
    enabled: params.from !== '' && params.to !== '',
    refetchInterval: AUTO_REFRESH_INTERVAL_MS,
  });
