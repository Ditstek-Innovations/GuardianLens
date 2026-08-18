import { useQuery } from '@tanstack/react-query';

import { apiClient } from '@/lib/api/client';
import { unwrapItems } from '@/lib/api/list';

import type { AuditEntry, ListResponse } from '@/lib/api/types';

const auditKeys = {
  all: ['audit'] as const,
  list: () => [...auditKeys.all, 'list'] as const,
};

/**
 * GET /api/v1/audit — a [V1] endpoint (TRD §10.6); the MVP backend may not
 * serve it yet, in which case the page shows its explicit error state.
 * ASSUMPTION A-9 covers the response shape.
 */
export const useAuditQuery = () =>
  useQuery({
    queryKey: auditKeys.list(),
    queryFn: async ({ signal }) =>
      unwrapItems(
        await apiClient.get<ListResponse<AuditEntry> | AuditEntry[]>('/api/v1/audit', { signal }),
      ),
  });
