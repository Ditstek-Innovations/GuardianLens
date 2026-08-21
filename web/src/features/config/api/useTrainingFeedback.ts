import { useQuery } from '@tanstack/react-query';

import { apiClient } from '@/lib/api/client';

import { configKeys } from './configKeys';

import type { TrainingFeedback } from '@/lib/api/types';

export const useTrainingFeedback = () =>
  useQuery({
    queryKey: configKeys.trainingFeedback(),
    queryFn: () => apiClient.get<TrainingFeedback>('/api/v1/training-feedback'),
    refetchInterval: 10_000,
  });
