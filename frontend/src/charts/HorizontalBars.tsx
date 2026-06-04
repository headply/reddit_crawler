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

interface Props {
  data: LabelValue[];
  color?: string;
  multicolour?: boolean;
}

export function HorizontalBars({ data, color = "#2563EB", multicolour }: Props) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 5, right: 15, left: 5, bottom: 0 }}
      >
        <CartesianGrid stroke={GRID} horizontal={false} />
        <XAxis type="number" tick={AXIS_TICK} axisLine={AXIS_LINE} tickLine={false} />
        <YAxis
          dataKey="label"
          type="category"
          width={140}
          tick={{ ...AXIS_TICK, fontSize: 11 }}
          axisLine={AXIS_LINE}
          tickLine={false}
        />
        <Tooltip
          contentStyle={{
            background: "white",
            border: "1px solid #E2E8F0",
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Bar dataKey="value" radius={[0, 4, 4, 0]}>
          {data.map((_, idx) => (
            <Cell
              key={idx}
              fill={multicolour ? PALETTE[idx % PALETTE.length] : color}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
