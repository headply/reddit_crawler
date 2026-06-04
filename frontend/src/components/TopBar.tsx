import { Briefcase, Menu } from "lucide-react";
import { NavLink } from "react-router-dom";
import { useMeta } from "@/api/hooks";
import { formatNumber, timeAgo } from "@/lib/format";

const TABS = [
  { to: "/", label: "Browse" },
  { to: "/analytics", label: "Analytics" },
  { to: "/trends", label: "Tech Trends" },
  { to: "/sources", label: "Sources" },
];

export function TopBar({ onToggleSidebar }: { onToggleSidebar: () => void }) {
  const { data } = useMeta();
  return (
    <header className="sticky top-0 z-40 bg-white border-b border-line">
      <div className="px-4 sm:px-6 h-14 flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="lg:hidden inline-flex items-center justify-center w-9 h-9 rounded-md border border-line text-muted hover:bg-slate-50"
          aria-label="Open filters"
        >
          <Menu size={16} />
        </button>
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shrink-0">
            <Briefcase size={16} className="text-white" />
          </div>
          <div className="min-w-0">
            <div className="text-[14px] font-bold text-ink leading-tight">
              Job Intelligence
            </div>
            <div className="text-[11px] text-soft leading-tight hidden sm:block">
              Daily job listings from Reddit communities
            </div>
          </div>
        </div>

        <nav className="ml-auto flex items-center gap-1 overflow-x-auto">
          {TABS.map((t) => (
            <NavLink
              key={t.to}
              to={t.to}
              end={t.to === "/"}
              className={({ isActive }) =>
                "px-3 py-1.5 text-[13px] rounded-md font-medium transition-colors " +
                (isActive
                  ? "text-accent bg-chipBlue"
                  : "text-muted hover:text-ink hover:bg-slate-50")
              }
            >
              {t.label}
            </NavLink>
          ))}
        </nav>
      </div>
      {data && (
        <div className="hidden md:block text-[11px] text-soft px-6 pb-2 -mt-1">
          {formatNumber(data.total_jobs)} jobs · {formatNumber(data.total_posts)}{" "}
          posts scraped · {data.llm_classified_pct}% LLM-classified · last
          updated {timeAgo(data.latest_scraped_at)}
          {data.scams_flagged > 0 && (
            <>
              {" "}
              · {formatNumber(data.scams_flagged)} scams flagged
            </>
          )}
        </div>
      )}
    </header>
  );
}
