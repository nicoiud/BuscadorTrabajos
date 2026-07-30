import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  fetchJobs,
  generateCoverLetter,
  semanticSearchJobs,
  triggerEnrichment,
  triggerIngestion,
} from "../api/jobs";
import type { SearchPreferences } from "./usePreferences";

export type SearchMode = "keyword" | "semantic";

export function useJobs(query: string, mode: SearchMode, preferences: SearchPreferences) {
  return useQuery({
    queryKey: ["jobs", mode, query, preferences],
    queryFn: () =>
      mode === "semantic" ? semanticSearchJobs(query, preferences) : fetchJobs(query, preferences),
    enabled: mode === "keyword" || query.trim().length > 0,
  });
}

export function useTriggerIngestion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: triggerIngestion,
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

export function useGenerateCoverLetter() {
  return useMutation({
    mutationFn: ({ jobId, profileText }: { jobId: string; profileText: string }) =>
      generateCoverLetter(jobId, profileText),
  });
}
