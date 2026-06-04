import { useAnalytics } from "@/api/hooks";
import { ChartCard } from "@/components/ChartCard";
import { Donut } from "@/charts/Donut";
import { HorizontalBars } from "@/charts/HorizontalBars";
import { VerticalBars } from "@/charts/VerticalBars";
import { VolumeOverTime } from "@/charts/VolumeOverTime";
import { SalaryByRole } from "@/charts/SalaryByRole";
import { WORK_MODE_COLORS } from "@/lib/theme";
import { useFilterState } from "@/state/filters";

const SENIORITY_ORDER = [
  "Intern", "Junior", "Mid", "Senior", "Staff",
  "Principal", "Lead/Manager", "Director+",
];

export function AnalyticsPage() {
  const { filters } = useFilterState();
  const { data, isLoading } = useAnalytics(filters);

  if (isLoading || !data) return <Loading />;

  const seniority = [...data.seniority_breakdown].sort(
    (a, b) =>
      SENIORITY_ORDER.indexOf(a.label) - SENIORITY_ORDER.indexOf(b.label),
  );

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <ChartCard title="Job volume over time">
          <VolumeOverTime data={data.volume_over_time} />
        </ChartCard>
        <ChartCard title="Top subreddits">
          <HorizontalBars data={data.top_subreddits} color="#2563EB" />
        </ChartCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <ChartCard title="Domain breakdown" height={320}>
          <Donut data={data.domain_breakdown} />
        </ChartCard>
        <ChartCard title="Work mode split" height={320}>
          <Donut data={data.work_mode_split} colorMap={WORK_MODE_COLORS} />
        </ChartCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <ChartCard title="Seniority breakdown">
          <VerticalBars data={seniority} />
        </ChartCard>
        <ChartCard title="Job type breakdown">
          <HorizontalBars data={data.job_type_breakdown} color="#0EA5E9" />
        </ChartCard>
      </div>

      <ChartCard title="Top 20 in-demand skills" height={520}>
        <HorizontalBars data={data.top_skills} multicolour />
      </ChartCard>

      <ChartCard
        title="Salary distribution by role"
        subtitle="Median, P25–P75 range for (domain × seniority) combos with ≥ 5 samples"
        height={Math.max(220, data.salary_by_role.length * 36 + 60)}
      >
        <SalaryByRole data={data.salary_by_role} />
      </ChartCard>
    </div>
  );
}

function Loading() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          className="bg-white border border-line rounded-xl h-72 animate-pulse"
        />
      ))}
    </div>
  );
}
