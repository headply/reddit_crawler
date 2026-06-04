import { Disclosure } from "@headlessui/react";
import { ChevronDown, RefreshCw, RotateCcw, Search } from "lucide-react";
import { useFilters } from "@/api/hooks";
import type { DateRange, FilterState } from "@/api/types";
import { useFilterState } from "@/state/filters";
import { CategoryToggle } from "./CategoryToggle";

const DATE_OPTIONS: { value: DateRange; label: string }[] = [
  { value: "today", label: "Today" },
  { value: "7d", label: "7 days" },
  { value: "30d", label: "30 days" },
  { value: "90d", label: "90 days" },
  { value: "all", label: "All" },
];

export function Sidebar({ onRefresh }: { onRefresh?: () => void }) {
  const { filters, setFilter, toggleMulti, reset } = useFilterState();
  const { data: opts } = useFilters();

  return (
    <aside className="w-full lg:w-72 lg:shrink-0 bg-white border border-line lg:border-0 lg:border-r rounded-xl lg:rounded-none p-4 lg:p-0 lg:h-[calc(100vh-56px)] lg:sticky lg:top-14 overflow-y-auto">
      <div className="lg:px-4 lg:pt-4 lg:pb-2 lg:border-b lg:border-line">
        <h2 className="text-[13px] font-bold text-ink">Filters</h2>
        <p className="text-[11px] text-soft mt-0.5">
          {filters.exclude_scams ? "Scams hidden" : "Scams visible"} ·{" "}
          {filters.date_range}
        </p>
      </div>

      <div className="lg:px-4 lg:py-3 space-y-4">
        {/* Show on mobile only — desktop has it in the top bar */}
        <div className="md:hidden">
          <Label>Show</Label>
          <CategoryToggle />
        </div>

        {/* Date range */}
        <div>
          <Label>Time range</Label>
          <div className="flex flex-wrap gap-1">
            {DATE_OPTIONS.map((o) => (
              <button
                key={o.value}
                onClick={() => setFilter("date_range", o.value)}
                className={
                  "px-2.5 py-1 text-[12px] rounded-md border transition-colors " +
                  (filters.date_range === o.value
                    ? "bg-primary text-white border-primary"
                    : "bg-white text-muted border-line hover:bg-slate-50")
                }
              >
                {o.label}
              </button>
            ))}
          </div>
        </div>

        {/* Search */}
        <div>
          <Label>Search</Label>
          <div className="relative">
            <Search
              size={14}
              className="absolute left-2.5 top-1/2 -translate-y-1/2 text-soft"
            />
            <input
              type="text"
              value={filters.search}
              onChange={(e) => setFilter("search", e.target.value)}
              placeholder="Title, skill, company..."
              className="w-full pl-8 pr-2 py-1.5 text-[13px] border border-line rounded-md bg-white focus:outline-none focus:border-accent"
            />
          </div>
        </div>

        {/* Quality */}
        <div className="space-y-2">
          <Label>Quality</Label>
          <label className="flex items-center justify-between text-[12px] text-ink cursor-pointer">
            <span>Hide scam-flagged</span>
            <Toggle
              checked={filters.exclude_scams}
              onChange={(v) => setFilter("exclude_scams", v)}
            />
          </label>
          <div>
            <div className="flex items-center justify-between text-[12px]">
              <span className="text-muted">Min confidence</span>
              <span className="text-ink font-medium">
                {Math.round(filters.min_confidence * 100)}%
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={Math.round(filters.min_confidence * 100)}
              onChange={(e) =>
                setFilter("min_confidence", Number(e.target.value) / 100)
              }
              className="w-full accent-accent"
            />
          </div>
        </div>

        <Facet
          label="Domain"
          options={opts?.domains ?? []}
          selected={filters.domain}
          onToggle={(v) => toggleMulti("domain", v)}
        />
        <Facet
          label="Job type"
          options={opts?.job_types ?? []}
          selected={filters.job_type}
          onToggle={(v) => toggleMulti("job_type", v)}
        />
        <Facet
          label="Seniority"
          options={opts?.seniorities ?? []}
          selected={filters.seniority}
          onToggle={(v) => toggleMulti("seniority", v)}
        />
        <Facet
          label="Work mode"
          options={opts?.work_modes ?? []}
          selected={filters.work_mode}
          onToggle={(v) => toggleMulti("work_mode", v)}
        />
        <Facet
          label="Tech stack"
          options={opts?.techs ?? []}
          selected={filters.tech}
          onToggle={(v) => toggleMulti("tech", v)}
          collapsedDefault
        />
        <Facet
          label="Subreddit"
          options={opts?.subreddits ?? []}
          selected={filters.subreddit}
          onToggle={(v) => toggleMulti("subreddit", v)}
          collapsedDefault
        />

        <div className="flex gap-2 pt-2 border-t border-line">
          <button
            onClick={reset}
            className="flex-1 inline-flex items-center justify-center gap-1.5 text-[12px] font-medium text-muted border border-line bg-white hover:bg-slate-50 rounded-md py-1.5"
          >
            <RotateCcw size={12} /> Reset
          </button>
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="flex-1 inline-flex items-center justify-center gap-1.5 text-[12px] font-medium text-muted border border-line bg-white hover:bg-slate-50 rounded-md py-1.5"
            >
              <RefreshCw size={12} /> Refresh
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[10.5px] uppercase tracking-wider font-bold text-soft mb-1.5">
      {children}
    </div>
  );
}

function Toggle({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={
        "relative inline-flex h-5 w-9 items-center rounded-full transition-colors " +
        (checked ? "bg-accent" : "bg-line")
      }
    >
      <span
        className={
          "inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform " +
          (checked ? "translate-x-5" : "translate-x-1")
        }
      />
    </button>
  );
}

function Facet({
  label,
  options,
  selected,
  onToggle,
  collapsedDefault = false,
}: {
  label: string;
  options: string[];
  selected: string[];
  onToggle: (v: string) => void;
  collapsedDefault?: boolean;
}) {
  return (
    <Disclosure defaultOpen={!collapsedDefault && options.length > 0 && options.length <= 12}>
      {({ open }) => (
        <>
          <Disclosure.Button className="w-full flex items-center justify-between text-[12px] font-semibold text-muted">
            <span>
              {label}
              {selected.length > 0 && (
                <span className="ml-1.5 inline-flex items-center justify-center text-[10px] font-bold text-accent bg-chipBlue rounded-full px-1.5 py-[1px]">
                  {selected.length}
                </span>
              )}
            </span>
            <ChevronDown
              size={14}
              className={"transition-transform " + (open ? "rotate-180" : "")}
            />
          </Disclosure.Button>
          <Disclosure.Panel className="mt-1.5 space-y-0.5 max-h-48 overflow-y-auto pr-1">
            {options.length === 0 && (
              <div className="text-[11px] text-soft py-1">No options yet.</div>
            )}
            {options.map((opt) => (
              <label
                key={opt}
                className="flex items-center gap-2 text-[12.5px] text-ink hover:bg-slate-50 rounded px-1 py-1 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={selected.includes(opt)}
                  onChange={() => onToggle(opt)}
                  className="rounded border-line text-accent"
                />
                <span className="truncate">{opt}</span>
              </label>
            ))}
          </Disclosure.Panel>
        </>
      )}
    </Disclosure>
  );
}
