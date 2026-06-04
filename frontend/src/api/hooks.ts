import { useQuery } from "@tanstack/react-query";
import { apiGet, filtersToQuery } from "./client";
import type {
  AnalyticsResponse,
  FiltersResponse,
  FilterState,
  JobsResponse,
  MetaResponse,
  SubredditHealthResponse,
  TechTrendsResponse,
} from "./types";

export function useMeta() {
  return useQuery({
    queryKey: ["meta"],
    queryFn: () => apiGet<MetaResponse>("/meta"),
    staleTime: 60_000,
    gcTime: 300_000,
  });
}

export function useFilters() {
  return useQuery({
    queryKey: ["filters"],
    queryFn: () => apiGet<FiltersResponse>("/filters"),
    staleTime: 300_000,
    gcTime: 600_000,
  });
}

export function useJobs(filters: FilterState, page: number, pageSize: number) {
  const qs = filtersToQuery(filters, { page, page_size: pageSize });
  return useQuery({
    queryKey: ["jobs", filters, page, pageSize],
    queryFn: () => apiGet<JobsResponse>(`/jobs${qs}`),
    staleTime: 30_000,
    gcTime: 300_000,
  });
}

export function useAnalytics(filters: FilterState) {
  const qs = filtersToQuery(filters);
  return useQuery({
    queryKey: ["analytics", filters],
    queryFn: () => apiGet<AnalyticsResponse>(`/analytics${qs}`),
    staleTime: 60_000,
    gcTime: 300_000,
  });
}

export function useTechTrends(filters: FilterState) {
  const qs = filtersToQuery(filters);
  return useQuery({
    queryKey: ["tech-trends", filters],
    queryFn: () => apiGet<TechTrendsResponse>(`/tech-trends${qs}`),
    staleTime: 60_000,
    gcTime: 300_000,
  });
}

export function useSubredditHealth() {
  return useQuery({
    queryKey: ["subreddit-health"],
    queryFn: () => apiGet<SubredditHealthResponse>("/subreddit-health"),
    staleTime: 300_000,
    gcTime: 600_000,
  });
}
