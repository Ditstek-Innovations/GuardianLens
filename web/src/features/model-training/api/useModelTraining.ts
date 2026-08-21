import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/api/client";

import type { TrainingFeedback } from "@/lib/api/types";

export const useModelTraining = () =>
  useQuery({
    queryKey: ["model-training", "status"],
    queryFn: () => apiClient.get<TrainingFeedback>("/api/v1/training-feedback"),
    refetchInterval: 5_000,
  });
