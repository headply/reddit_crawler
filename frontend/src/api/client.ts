import type { FilterState } from "./types";

function toQuery(params: Record<string, string | number | boolean | string[] | undefined>): string {
  const out: string[] = [];
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null) continue;
    if (Array.isArray(v)) {
      if (v.length === 0) continue;
      out.push(`${encodeURIComponent(k)}=${encodeURIComponent(v.join(","))}`);
    } else if (typeof v === "boolean") {
      out.push(`${encodeURIComponent(k)}=${v ? "true" : "false"}`);
    } else if (v !== "") {
      out.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
    }
  }
  return out.length ? `?${out.join("&")}` : "";
}

export function filtersToQuery(filters: FilterState, extra: Record<string, string | number | undefined> = {}): string {
  return toQuery({
    search: filters.search,
    domain: filters.domain,
    job_type: filters.job_type,
    seniority: filters.seniority,
    work_mode: filters.work_mode,
    tech: filters.tech,
    subreddit: filters.subreddit,
    categories: filters.categories,
    date_range: filters.date_range,
    exclude_scams: filters.exclude_scams,
    min_confidence: filters.min_confidence > 0 ? filters.min_confidence : undefined,
    ...extra,
  });
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`/api${path}`, { headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} on ${path}`);
  return (await res.json()) as T;
}
