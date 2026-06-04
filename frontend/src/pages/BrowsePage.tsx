import { useState } from "react";
import { JobCard } from "@/components/JobCard";
import { KpiStrip } from "@/components/KpiStrip";
import { Pagination } from "@/components/Pagination";
import { useJobs } from "@/api/hooks";
import { useFilterState } from "@/state/filters";

const PAGE_SIZE = 20;

export function BrowsePage() {
  const { filters } = useFilterState();
  const [page, setPage] = useState(1);
  const { data, isLoading, error } = useJobs(filters, page, PAGE_SIZE);

  if (error) {
    return (
      <div className="bg-white border border-line rounded-xl p-6 text-sm text-danger">
        Failed to load jobs: {(error as Error).message}
      </div>
    );
  }

  return (
    <div>
      {data ? <KpiStrip kpis={data.kpis} /> : <KpiSkeleton />}

      {isLoading && !data ? (
        <ListSkeleton />
      ) : data && data.items.length === 0 ? (
        <div className="bg-white border border-line rounded-xl p-8 text-center text-sm text-muted">
          No jobs match the current filters.
        </div>
      ) : data ? (
        <>
          <div className="space-y-2.5">
            {data.items.map((j) => (
              <JobCard key={j.post_id} job={j} />
            ))}
          </div>
          <Pagination
            page={data.page}
            pages={data.pages}
            total={data.total}
            onChange={(p) => {
              setPage(p);
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
          />
        </>
      ) : null}
    </div>
  );
}

function KpiSkeleton() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-5">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="bg-white border border-line rounded-xl shadow-card h-[58px] animate-pulse"
        />
      ))}
    </div>
  );
}
function ListSkeleton() {
  return (
    <div className="space-y-2.5">
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="bg-white border border-line rounded-xl shadow-card h-[140px] animate-pulse"
        />
      ))}
    </div>
  );
}
