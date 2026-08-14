import { useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';

import { Skeleton } from '@/components/ui';
import { apiClient } from '@/lib/api/client';

/**
 * A small evidence-frame thumbnail for history rows. Same authenticated
 * blob fetch as the detail page's EvidenceFrame; cached per event, never
 * refetched (a capture is immutable). Rows without evidence render an
 * honest dash, never a broken image.
 */
export const EvidenceThumb = ({
  evidenceUrl,
  eventId,
}: {
  readonly evidenceUrl: string | null;
  readonly eventId: string;
}) => {
  const query = useQuery({
    queryKey: ['history', 'evidence-thumb', eventId],
    queryFn: ({ signal }) => apiClient.getBlob(evidenceUrl ?? '', { signal }),
    enabled: evidenceUrl !== null,
    staleTime: Infinity,
    gcTime: 5 * 60 * 1000,
  });

  const objectUrl = useMemo(
    () => (query.data !== undefined ? URL.createObjectURL(query.data) : null),
    [query.data],
  );
  useEffect(
    () => () => {
      if (objectUrl !== null) URL.revokeObjectURL(objectUrl);
    },
    [objectUrl],
  );

  if (evidenceUrl === null) {
    return <span className="text-sm text-fg-faint">—</span>;
  }
  if (query.isPending) {
    return <Skeleton className="h-12 w-20 rounded-control" />;
  }
  if (query.isError || objectUrl === null) {
    return <span className="text-sm text-fg-faint">unavailable</span>;
  }
  return (
    <img
      src={objectUrl}
      alt="Evidence frame"
      loading="lazy"
      className="h-12 w-20 rounded-control border border-border object-cover"
    />
  );
};
