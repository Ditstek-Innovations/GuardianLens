import { useEffect, useMemo } from 'react';

import { Skeleton } from '@/components/ui';

import { useLiveFrame } from '../api/useLiveFrame';

export const LiveFrame = ({ cameraId, cameraName }: { cameraId: string; cameraName: string }) => {
  const query = useLiveFrame(cameraId);
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

  if (query.isPending) {
    return <Skeleton className="aspect-video w-full rounded-card" />;
  }
  if (query.isError || objectUrl === null) {
    return (
      <div className="flex aspect-video items-center justify-center rounded-card bg-surface-2 px-6 text-center text-sm text-fg-muted">
        Waiting for the edge agent to publish a live preview…
      </div>
    );
  }
  return (
    <img
      src={objectUrl}
      alt={`Near-live preview from ${cameraName}`}
      className="aspect-video w-full rounded-card bg-black object-contain"
    />
  );
};
