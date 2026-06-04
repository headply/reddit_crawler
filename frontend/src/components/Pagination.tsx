import { ChevronLeft, ChevronRight } from "lucide-react";
import { formatNumber } from "@/lib/format";

interface PaginationProps {
  page: number;
  pages: number;
  total: number;
  onChange: (page: number) => void;
}

export function Pagination({ page, pages, total, onChange }: PaginationProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 py-3 mt-1 border-t border-line">
      <div className="text-xs text-soft">{formatNumber(total)} listings</div>
      <div className="flex items-center gap-2">
        <button
          className="px-2.5 py-1.5 text-xs rounded-md border border-line bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed inline-flex items-center gap-1"
          onClick={() => onChange(page - 1)}
          disabled={page <= 1}
        >
          <ChevronLeft size={14} /> Prev
        </button>
        <span className="text-xs text-muted px-2">
          Page <strong className="text-ink">{page}</strong> of {pages}
        </span>
        <button
          className="px-2.5 py-1.5 text-xs rounded-md border border-line bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed inline-flex items-center gap-1"
          onClick={() => onChange(page + 1)}
          disabled={page >= pages}
        >
          Next <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}
