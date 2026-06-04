import { createContext, useCallback, useContext, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { EMPTY_FILTERS, type DateRange, type FilterState } from "@/api/types";

interface FilterContextValue {
  filters: FilterState;
  setFilter: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void;
  toggleMulti: (key: keyof FilterState, value: string) => void;
  reset: () => void;
}

const Ctx = createContext<FilterContextValue | null>(null);

const CSV_KEYS: (keyof FilterState)[] = [
  "domain", "job_type", "seniority", "work_mode", "tech", "subreddit",
];

function parseFromSearch(sp: URLSearchParams): FilterState {
  const out: FilterState = { ...EMPTY_FILTERS };
  for (const k of CSV_KEYS) {
    const v = sp.get(k);
    if (v) (out as any)[k] = v.split(",").filter(Boolean);
  }
  const search = sp.get("search");
  if (search) out.search = search;
  const dr = sp.get("date_range") as DateRange | null;
  if (dr) out.date_range = dr;
  const ex = sp.get("exclude_scams");
  if (ex !== null) out.exclude_scams = ex !== "false";
  const mc = sp.get("min_confidence");
  if (mc) out.min_confidence = Number(mc) || 0;
  return out;
}

function applyToSearch(filters: FilterState, sp: URLSearchParams): URLSearchParams {
  const out = new URLSearchParams(sp);
  for (const k of CSV_KEYS) {
    const arr = filters[k] as string[];
    if (arr.length) out.set(k, arr.join(","));
    else out.delete(k);
  }
  filters.search ? out.set("search", filters.search) : out.delete("search");
  out.set("date_range", filters.date_range);
  if (!filters.exclude_scams) out.set("exclude_scams", "false");
  else out.delete("exclude_scams");
  if (filters.min_confidence > 0) out.set("min_confidence", String(filters.min_confidence));
  else out.delete("min_confidence");
  return out;
}

export function FilterProvider({ children }: { children: React.ReactNode }) {
  const [sp, setSp] = useSearchParams();
  const filters = useMemo(() => parseFromSearch(sp), [sp]);

  const setFilter = useCallback(
    <K extends keyof FilterState>(key: K, value: FilterState[K]) => {
      const next = { ...filters, [key]: value };
      setSp(applyToSearch(next, sp), { replace: true });
    },
    [filters, sp, setSp],
  );

  const toggleMulti = useCallback(
    (key: keyof FilterState, value: string) => {
      const current = filters[key] as string[];
      const next = current.includes(value)
        ? current.filter((v) => v !== value)
        : [...current, value];
      setFilter(key, next as any);
    },
    [filters, setFilter],
  );

  const reset = useCallback(() => setSp(new URLSearchParams(), { replace: true }), [setSp]);

  const value: FilterContextValue = { filters, setFilter, toggleMulti, reset };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useFilterState(): FilterContextValue {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useFilterState must be used inside FilterProvider");
  return ctx;
}
