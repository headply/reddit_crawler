import { useMemo } from "react";
import type { Heatmap } from "@/api/types";

function interpolate(value: number, max: number): string {
  if (max === 0) return "#F8FAFC";
  const t = Math.sqrt(value / max); // sqrt to emphasise low values
  const r = Math.round(0xf8 + (0x1e - 0xf8) * t);
  const g = Math.round(0xfa + (0x3a - 0xfa) * t);
  const b = Math.round(0xfc + (0x5f - 0xfc) * t);
  return `rgb(${r}, ${g}, ${b})`;
}

export function TechDomainHeatmap({ data }: { data: Heatmap }) {
  const max = useMemo(
    () => data.matrix.flat().reduce((m, v) => Math.max(m, v), 0),
    [data],
  );

  if (data.domains.length === 0 || data.techs.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-soft">
        Not enough data for the heatmap.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto h-full">
      <div className="min-w-[640px]">
        <div className="grid" style={{ gridTemplateColumns: `160px repeat(${data.techs.length}, minmax(38px, 1fr))` }}>
          <div />
          {data.techs.map((t) => (
            <div
              key={t}
              className="text-[10px] text-muted font-medium px-1 py-2 text-center truncate"
              title={t}
            >
              {t}
            </div>
          ))}
          {data.domains.map((d, di) => (
            <DomainRow
              key={d}
              label={d}
              cells={data.matrix[di]}
              techs={data.techs}
              max={max}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function DomainRow({
  label,
  cells,
  techs,
  max,
}: {
  label: string;
  cells: number[];
  techs: string[];
  max: number;
}) {
  return (
    <>
      <div
        className="text-[11px] text-ink font-medium pr-2 py-1.5 text-right truncate"
        title={label}
      >
        {label}
      </div>
      {cells.map((v, ti) => (
        <div
          key={techs[ti]}
          className="aspect-square flex items-center justify-center rounded text-[10px] font-semibold border border-white"
          style={{
            background: interpolate(v, max),
            color: v > max * 0.5 ? "white" : "#475569",
            minHeight: 30,
          }}
          title={`${label} × ${techs[ti]}: ${v}`}
        >
          {v > 0 ? v : ""}
        </div>
      ))}
    </>
  );
}
