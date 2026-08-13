import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { EVIDENCE_STALE_TIME_MS } from '@/constants/query';
import { apiClient } from '@/lib/api/client';

import { eventKeys } from './eventKeys';

export interface EvidenceState {
  readonly url: string | null;
  readonly isPending: boolean;
  readonly isError: boolean;
}

/**
 * The evidence frame arrives as an authenticated blob (bearer header on the
 * request), not a plain <img src> URL — TRD §10.4 authorises evidence access
 * per caller. The blob is surfaced as an object URL.
 */
export const useEvidence = (eventId: string): EvidenceState => {
  const query = useQuery({
    queryKey: eventKeys.evidence(eventId),
    queryFn: ({ signal }) => apiClient.getBlob(`/api/v1/events/${eventId}/evidence`, { signal }),
    staleTime: EVIDENCE_STALE_TIME_MS,
    retry: 1,
    enabled: eventId !== '',
  });

  const blob = query.data;
  const [url, setUrl] = useState<string | null>(null);

  // Object-URL lifecycle is an external browser resource, created and revoked
  // in sync with the blob (CS-S-03).
  useEffect(() => {
    if (blob === undefined) return undefined;
    const objectUrl = URL.createObjectURL(blob);
    setUrl(objectUrl);
    return () => {
      URL.revokeObjectURL(objectUrl);
      setUrl(null);
    };
  }, [blob]);

  return { url, isPending: query.isPending, isError: query.isError };
};
