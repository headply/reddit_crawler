import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { LabelValue } from "@/api/types";
import { PALETTE } from "@/lib/theme";
import { AXIS_LINE, AXIS_TICK, GRID } from "./common";

export function VerticalBars({ data }: { data: LabelValue[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="label" tick={AXIS_TICK} axisLine={AXIS_LINE} tickLine={false} />
        <YAxis tick={AXIS_TICK} axisLine={AXIS_LINE} tickLine={false} allowDecimals={false} />
        <Tooltip
          contentStyle={{
            background: "white",
            border: "1px solid #E2E8F0",
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
          {data.map((_, i) => (
            <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
