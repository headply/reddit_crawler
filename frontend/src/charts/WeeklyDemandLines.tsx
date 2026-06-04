import { useMemo } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { WeeklyDemandPoint } from "@/api/types";
import { PALETTE } from "@/lib/theme";
import { AXIS_LINE, AXIS_TICK, GRID } from "./common";

export function WeeklyDemandLines({ data }: { data: WeeklyDemandPoint[] }) {
  const { series, weeks } = useMemo(() => {
    const weeksSet = new Set<string>();
    const seriesMap = new Map<string, Map<string, number>>();
    for (const p of data) {
      weeksSet.add(p.week);
      if (!seriesMap.has(p.tech)) seriesMap.set(p.tech, new Map());
      seriesMap.get(p.tech)!.set(p.week, p.count);
    }
    const weeks = Array.from(weeksSet).sort();
    const series: string[] = Array.from(seriesMap.keys());
    return { series, weeks, seriesMap };
  }, [data]);

  const pivot = useMemo(() => {
    const seriesMap = new Map<string, Map<string, number>>();
    for (const p of data) {
      if (!seriesMap.has(p.tech)) seriesMap.set(p.tech, new Map());
      seriesMap.get(p.tech)!.set(p.week, p.count);
    }
    return weeks.map((w) => {
      const row: Record<string, string | number> = { week: w };
      for (const tech of series) {
        row[tech] = seriesMap.get(tech)?.get(w) ?? 0;
      }
      return row;
    });
  }, [data, weeks, series]);

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={pivot} margin={{ top: 10, right: 5, left: -10, bottom: 0 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="week" tick={AXIS_TICK} axisLine={AXIS_LINE} tickLine={false} minTickGap={20} />
        <YAxis tick={AXIS_TICK} axisLine={AXIS_LINE} tickLine={false} allowDecimals={false} />
        <Tooltip
          contentStyle={{
            background: "white",
            border: "1px solid #E2E8F0",
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Legend
          verticalAlign="top"
          height={28}
          iconSize={10}
          wrapperStyle={{ fontSize: 11, color: "#64748B" }}
        />
        {series.map((tech, i) => (
          <Line
            key={tech}
            type="monotone"
            dataKey={tech}
            stroke={PALETTE[i % PALETTE.length]}
            strokeWidth={2}
            dot={{ r: 2.5 }}
            activeDot={{ r: 4 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
