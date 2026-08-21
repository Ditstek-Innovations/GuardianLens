import { useMutation, useQueryClient } from '@tanstack/react-query';

import { apiClient } from '@/lib/api/client';

import { configKeys } from './configKeys';

export const useDeleteCamera = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (cameraId: string) => apiClient.delete<void>(`/api/v1/cameras/${cameraId}`),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: configKeys.all });
    },
  });
};
