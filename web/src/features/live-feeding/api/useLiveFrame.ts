import { useQuery } from '@tanstack/react-query';

import { apiClient } from '@/lib/api/client';

export const useLiveFrame = (cameraId: string) =>
  useQuery({
    queryKey: ['live-feeding', 'frame', cameraId],
    queryFn: ({ signal }) =>
      apiClient.getBlob(`/api/v1/cameras/${cameraId}/live-frame`, { signal }),
    retry: false,
    staleTime: 0,
    refetchInterval: 1_000,
    refetchIntervalInBackground: false,
  });
