import { Briefcase, Cpu, Globe, Layers, Zap } from "lucide-react";
import type { Kpis } from "@/api/types";
import { formatNumber } from "@/lib/format";

interface Tile {
  label: string;
  value: string;
  icon: React.ReactNode;
  bg: string;
}

export function KpiStrip({ kpis }: { kpis: Kpis }) {
  const tiles: Tile[] = [
    {
      label: "Job posts",
      value: formatNumber(kpis.total_jobs),
      icon: <Briefcase size={18} className="text-accent" />,
      bg: "bg-chipBlue",
    },
    {
      label: "New last 24 h",
      value: formatNumber(kpis.new_24h),
      icon: <Zap size={18} className="text-ok" />,
      bg: "bg-chipGreen",
    },
    {
      label: "Remote",
      value: `${kpis.remote_pct}%`,
      icon: <Globe size={18} className="text-warn" />,
      bg: "bg-chipAmber",
    },
    {
      label: "Top domain",
      value: kpis.top_domain ? kpis.top_domain.split(" ")[0] : "—",
      icon: <Layers size={18} className="text-[#7C3AED]" />,
      bg: "bg-chipViolet",
    },
    {
      label: "Tech skills",
      value: formatNumber(kpis.tech_skills),
      icon: <Cpu size={18} className="text-slate-600" />,
      bg: "bg-slate-100",
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-5">
      {tiles.map((t) => (
        <div
          key={t.label}
          className="bg-white border border-line rounded-xl shadow-card px-3 py-3 flex items-center gap-3"
        >
          <div
            className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${t.bg}`}
          >
            {t.icon}
          </div>
          <div className="min-w-0">
            <div className="text-lg font-bold text-ink leading-none">{t.value}</div>
            <div className="text-[11px] text-soft font-medium mt-1 truncate">
              {t.label}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
