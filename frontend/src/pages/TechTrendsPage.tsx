import { useTechTrends } from "@/api/hooks";
import { ChartCard } from "@/components/ChartCard";
import { TechDomainHeatmap } from "@/charts/TechDomainHeatmap";
import { WeeklyDemandLines } from "@/charts/WeeklyDemandLines";
import { useFilterState } from "@/state/filters";

export function TechTrendsPage() {
  const { filters } = useFilterState();
  const { data, isLoading } = useTechTrends(filters);

  if (isLoading || !data) {
    return (
      <div className="bg-white border border-line rounded-xl h-72 animate-pulse" />
    );
  }

  return (
    <div className="space-y-3">
      <ChartCard
        title="Weekly demand"
        subtitle="Top 8 technologies in the current filter slice"
        height={360}
      >
        <WeeklyDemandLines data={data.weekly_demand} />
      </ChartCard>

      <ChartCard
        title="Tech × Domain (heatmap)"
        subtitle="Counts of posts mentioning each tech, by domain"
        height={Math.max(280, data.heatmap.domains.length * 36 + 60)}
      >
        <TechDomainHeatmap data={data.heatmap} />
      </ChartCard>

      <ChartCard
        title="Common tech combinations"
        subtitle="Top 15 co-occurring pairs in the current slice"
        height={Math.max(220, data.pairs.length * 28 + 50)}
      >
        {data.pairs.length === 0 ? (
          <div className="flex items-center justify-center h-full text-sm text-soft">
            No tech pairs found.
          </div>
        ) : (
          <table className="w-full text-[12px]">
            <thead>
              <tr className="text-[10px] uppercase tracking-wider text-soft">
                <th className="text-left pb-2">Pair</th>
                <th className="text-right pb-2 w-24">Co-occurrences</th>
              </tr>
            </thead>
            <tbody>
              {data.pairs.map((p) => (
                <tr
                  key={`${p.a}-${p.b}`}
                  className="border-t border-line"
                >
                  <td className="py-1.5 text-ink">
                    <span className="font-mono">{p.a}</span>
                    <span className="text-soft px-1.5">+</span>
                    <span className="font-mono">{p.b}</span>
                  </td>
                  <td className="py-1.5 text-right text-ink font-semibold tabular-nums">
                    {p.count}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </ChartCard>
    </div>
  );
}
