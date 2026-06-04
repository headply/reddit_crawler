import { clsx } from "@/lib/format";

export type BadgeTone =
  | "blue" | "green" | "amber" | "rose" | "violet" | "slate" | "outline";

const TONES: Record<BadgeTone, string> = {
  blue:    "bg-chipBlue text-[#1D4ED8]",
  green:   "bg-chipGreen text-[#065F46]",
  amber:   "bg-chipAmber text-[#92400E]",
  rose:    "bg-chipRose text-[#991B1B]",
  violet:  "bg-chipViolet text-[#5B21B6]",
  slate:   "bg-slate-100 text-slate-700",
  outline: "bg-white text-slate-600 border border-line",
};

export function Badge({
  children, tone = "slate", className,
}: {
  children: React.ReactNode;
  tone?: BadgeTone;
  className?: string;
}) {
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2 py-[2px] rounded text-[11px] font-semibold whitespace-nowrap",
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function workModeTone(mode?: string | null): BadgeTone {
  if (mode === "Remote") return "green";
  if (mode === "Hybrid") return "amber";
  if (mode === "On-site") return "rose";
  return "blue";
}

export function seniorityTone(level?: string | null): BadgeTone {
  if (level === "Junior" || level === "Intern") return "green";
  if (level === "Mid") return "blue";
  if (level === "Senior" || level === "Staff" || level === "Principal") return "violet";
  if (level === "Lead/Manager" || level === "Director+") return "amber";
  return "blue";
}
