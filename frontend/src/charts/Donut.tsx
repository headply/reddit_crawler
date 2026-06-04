import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { LabelValue } from "@/api/types";
import { PALETTE } from "@/lib/theme";

interface Props {
  data: LabelValue[];
  colorMap?: Record<string, string>;
}

export function Donut({ data, colorMap }: Props) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="label"
          innerRadius="55%"
          outerRadius="85%"
          paddingAngle={2}
        >
          {data.map((entry, idx) => (
            <Cell
              key={idx}
              fill={colorMap?.[entry.label] ?? PALETTE[idx % PALETTE.length]}
            />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            background: "white",
            border: "1px solid #E2E8F0",
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Legend
          verticalAlign="bottom"
          height={28}
          iconSize={10}
          wrapperStyle={{ fontSize: 11, color: "#64748B" }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
