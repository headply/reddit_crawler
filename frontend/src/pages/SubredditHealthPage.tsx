import { useSubredditHealth } from "@/api/hooks";
import { ChartCard } from "@/components/ChartCard";
import { formatNumber, timeAgo } from "@/lib/format";

export function SubredditHealthPage() {
  const { data, isLoading } = useSubredditHealth();

  if (isLoading || !data) {
    return (
      <div className="bg-white border border-line rounded-xl h-96 animate-pulse" />
    );
  }

  return (
    <ChartCard
      title="Source quality"
      subtitle="Where the dataset actually comes from — jobs found per post scraped, by subreddit"
      height={Math.max(280, data.items.length * 32 + 60)}
    >
      <div className="overflow-x-auto h-full">
        <table className="w-full text-[12.5px] min-w-[640px]">
          <thead className="text-[10.5px] uppercase tracking-wider text-soft">
            <tr>
              <th className="text-left font-semibold pb-2">Subreddit</th>
              <th className="text-right font-semibold pb-2 w-24">Scraped</th>
              <th className="text-right font-semibold pb-2 w-24">Jobs</th>
              <th className="text-right font-semibold pb-2 w-24">Scams</th>
              <th className="text-right font-semibold pb-2 w-24">Job rate</th>
              <th className="text-right font-semibold pb-2 w-32">Last scraped</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((row) => (
              <tr key={row.subreddit} className="border-t border-line">
                <td className="py-2 text-ink font-medium">r/{row.subreddit}</td>
                <td className="py-2 text-right text-muted tabular-nums">
                  {formatNumber(row.posts_scraped)}
                </td>
                <td className="py-2 text-right text-ink font-semibold tabular-nums">
                  {formatNumber(row.jobs_found)}
                </td>
                <td className="py-2 text-right tabular-nums text-muted">
                  {row.scams_flagged > 0 ? (
                    <span className="text-danger">{row.scams_flagged}</span>
                  ) : (
                    "0"
                  )}
                </td>
                <td className="py-2 text-right text-muted tabular-nums">
                  {row.job_rate != null
                    ? `${Math.round(row.job_rate * 100)}%`
                    : "—"}
                </td>
                <td className="py-2 text-right text-soft">
                  {timeAgo(row.last_scraped)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </ChartCard>
  );
}
