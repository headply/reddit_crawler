import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DateValue } from "@/api/types";
import { AXIS_LINE, AXIS_TICK, GRID } from "./common";

export function VolumeOverTime({ data }: { data: DateValue[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="date" tick={AXIS_TICK} axisLine={AXIS_LINE} tickLine={false} minTickGap={20} />
        <YAxis tick={AXIS_TICK} axisLine={AXIS_LINE} tickLine={false} allowDecimals={false} />
        <Tooltip
          contentStyle={{
            background: "white",
            border: "1px solid #E2E8F0",
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Area
          type="monotone"
          dataKey="value"
          stroke="#2563EB"
          strokeWidth={2}
          fill="#2563EB"
          fillOpacity={0.08}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
