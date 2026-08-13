import { QueryClient } from '@tanstack/react-query';

import { ApiError } from '@/lib/api/errors';

/** CS-D-11 — retry only transient failures; a 4xx is never transient. */
const shouldRetry = (failureCount: number, error: unknown): boolean => {
  if (error instanceof ApiError && error.status < 500) return false;
  return failureCount < 2;
};

export const createQueryClient = (): QueryClient =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: shouldRetry, refetchOnWindowFocus: false },
      // A decision mutation is never auto-retried (CS-D-11): the endpoint has
      // no idempotency contract and a duplicate submit is a 409, not a no-op.
      mutations: { retry: false },
    },
  });
