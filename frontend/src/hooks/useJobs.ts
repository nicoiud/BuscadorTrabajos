import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { fetchJobs, triggerRemoteOkIngestion } from "../api/jobs";

export function useJobs(query: string) {
  return useQuery({
    queryKey: ["jobs", query],
    queryFn: () => fetchJobs(query),
  });
}

export function useTriggerIngestion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: triggerRemoteOkIngestion,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}
