import type { SalaryBox } from "@/api/types";

const SENIORITY_ORDER = [
  "Intern", "Junior", "Mid", "Senior", "Staff",
  "Principal", "Lead/Manager", "Director+",
];

export function SalaryByRole({ data }: { data: SalaryBox[] }) {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-soft">
        Not enough salary samples (need ≥ 5 per domain × seniority).
      </div>
    );
  }
  const domains = Array.from(new Set(data.map((d) => d.domain)));
  const max = Math.max(...data.map((d) => d.p75));

  return (
    <div className="overflow-x-auto h-full">
      <table className="w-full text-[12px] border-collapse min-w-[560px]">
        <thead>
          <tr className="text-[10px] uppercase tracking-wider text-soft">
            <th className="text-left font-semibold pb-2">Domain × Seniority</th>
            <th className="text-right font-semibold pb-2 w-20">P25</th>
            <th className="text-right font-semibold pb-2 w-20">Median</th>
            <th className="text-right font-semibold pb-2 w-20">P75</th>
            <th className="w-[40%] pb-2"></th>
            <th className="text-right font-semibold pb-2 w-10">n</th>
          </tr>
        </thead>
        <tbody>
          {domains.flatMap((domain) =>
            SENIORITY_ORDER.flatMap((seniority) => {
              const row = data.find(
                (d) => d.domain === domain && d.seniority === seniority,
              );
              if (!row) return [];
              return (
                <tr key={`${domain}-${seniority}`} className="border-t border-line">
                  <td className="py-1.5 pr-2 text-ink">
                    <span className="font-medium">{domain}</span>{" "}
                    <span className="text-soft">· {seniority}</span>
                  </td>
                  <td className="py-1.5 text-right text-muted tabular-nums">
                    {fmt(row.p25)}
                  </td>
                  <td className="py-1.5 text-right text-ink font-semibold tabular-nums">
                    {fmt(row.median)}
                  </td>
                  <td className="py-1.5 text-right text-muted tabular-nums">
                    {fmt(row.p75)}
                  </td>
                  <td className="py-1.5 px-2">
                    <Box row={row} max={max} />
                  </td>
                  <td className="py-1.5 text-right text-soft tabular-nums">
                    {row.sample_size}
                  </td>
                </tr>
              );
            }),
          )}
        </tbody>
      </table>
    </div>
  );
}

function Box({ row, max }: { row: SalaryBox; max: number }) {
  if (!max) return null;
  const left = (row.p25 / max) * 100;
  const width = ((row.p75 - row.p25) / max) * 100;
  const median = (row.median / max) * 100;
  return (
    <div className="relative h-2 bg-bg rounded">
      <div
        className="absolute h-2 rounded bg-chipBlue"
        style={{ left: `${left}%`, width: `${width}%` }}
      />
      <div
        className="absolute top-0 w-[2px] h-2 bg-primary"
        style={{ left: `${median}%` }}
      />
    </div>
  );
}

function fmt(n: number): string {
  if (n >= 1000) return `${Math.round(n / 1000)}k`;
  return String(n);
}
