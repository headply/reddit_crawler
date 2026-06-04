export function timeAgo(iso?: string | null): string {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const diff = Date.now() - then;
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return "just now";
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const d = Math.floor(hr / 24);
  if (d < 30) return `${d}d ago`;
  const mo = Math.floor(d / 30);
  if (mo < 12) return `${mo}mo ago`;
  return `${Math.floor(mo / 12)}y ago`;
}

export function formatNumber(n: number): string {
  return new Intl.NumberFormat("en-US").format(n);
}

export function formatCompensation(
  min?: number | null,
  max?: number | null,
  currency?: string | null,
  period?: string | null,
): string | null {
  if (min == null && max == null) return null;
  const cur = currency || "USD";
  const fmt = (v: number) =>
    v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v.toString();
  const suffix =
    period === "hourly"
      ? "/hr"
      : period === "monthly"
        ? "/mo"
        : period === "project"
          ? " /project"
          : "";
  if (min != null && max != null && min !== max)
    return `${cur} ${fmt(min)}–${fmt(max)}${suffix}`;
  return `${cur} ${fmt((min ?? max) as number)}${suffix}`;
}

export function clsx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}
