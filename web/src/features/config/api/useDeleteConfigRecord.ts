import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/lib/api/client";

import { configKeys } from "./configKeys";

export type DeletableConfigResource =
  "agents" | "zones" | "rules" | "model-versions";

export const useDeleteConfigRecord = (resource: DeletableConfigResource) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete<void>(`/api/v1/${resource}/${id}`),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: configKeys.all });
    },
  });
};
