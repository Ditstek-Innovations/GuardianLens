import { useMutation } from '@tanstack/react-query';

import { apiClient } from '@/lib/api/client';

export type PtzDirection = 'up' | 'down' | 'left' | 'right';

export const usePtzMove = (cameraId: string) =>
  useMutation({
    mutationFn: (direction: PtzDirection) =>
      apiClient.post(`/api/v1/cameras/${cameraId}/ptz`, { direction }),
  });
