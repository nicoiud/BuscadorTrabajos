import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  fetchJobs,
  generateCoverLetter,
  semanticSearchJobs,
  triggerEnrichment,
  triggerIngestion,
  type JobPosting,
} from "../api/jobs";
import type { SearchPreferences } from "./usePreferences";

export type SearchMode = "keyword" | "semantic";

const PAGE_SIZE = 20;

export interface UseJobsResult {
  items: JobPosting[];
  total: number;
  isLoading: boolean;
  isError: boolean;
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  fetchNextPage: () => void;
}

export function useJobs(query: string, mode: SearchMode, preferences: SearchPreferences): UseJobsResult {
  // Palabra clave usa paginación real (el total puede superar largo el límite por
  // página de la API) — "Búsqueda con IA" ya devuelve un top-K acotado y rankeado,
  // no necesita "cargar más".
  const keywordQuery = useInfiniteQuery({
    queryKey: ["jobs", "keyword", query, preferences],
    queryFn: ({ pageParam }) => fetchJobs(query, preferences, pageParam, PAGE_SIZE),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      const loaded = allPages.reduce((sum, page) => sum + page.items.length, 0);
      return loaded < lastPage.total ? loaded : undefined;
    },
    enabled: mode === "keyword",
  });

  const semanticQuery = useQuery({
    queryKey: ["jobs", "semantic", query, preferences],
    queryFn: () => semanticSearchJobs(query, preferences),
    enabled: mode === "semantic" && query.trim().length > 0,
  });

  if (mode === "semantic") {
    return {
      items: semanticQuery.data?.items ?? [],
      total: semanticQuery.data?.total ?? 0,
      isLoading: semanticQuery.isLoading,
      isError: semanticQuery.isError,
      hasNextPage: false,
      isFetchingNextPage: false,
      fetchNextPage: () => {},
    };
  }

  return {
    items: keywordQuery.data?.pages.flatMap((page) => page.items) ?? [],
    total: keywordQuery.data?.pages[0]?.total ?? 0,
    isLoading: keywordQuery.isLoading,
    isError: keywordQuery.isError,
    hasNextPage: keywordQuery.hasNextPage,
    isFetchingNextPage: keywordQuery.isFetchingNextPage,
    fetchNextPage: () => keywordQuery.fetchNextPage(),
  };
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
