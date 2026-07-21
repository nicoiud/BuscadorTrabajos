import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  fetchJobs,
  semanticSearchJobs,
  triggerEnrichment,
  triggerRemoteOkIngestion,
} from "../api/jobs";

export type SearchMode = "keyword" | "semantic";

export function useJobs(query: string, mode: SearchMode) {
  return useQuery({
    queryKey: ["jobs", mode, query],
    queryFn: () => (mode === "semantic" ? semanticSearchJobs(query) : fetchJobs(query)),
    enabled: mode === "keyword" || query.trim().length > 0,
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

export function useTriggerEnrichment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: triggerEnrichment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}
