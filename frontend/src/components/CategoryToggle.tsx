import { Briefcase, Hand, Hammer } from "lucide-react";
import type { PostCategory } from "@/api/types";
import { useFilterState } from "@/state/filters";
import { clsx } from "@/lib/format";

const OPTIONS: { value: PostCategory; label: string; icon: React.ReactNode }[] =
  [
    { value: "hiring", label: "Hiring", icon: <Briefcase size={12} /> },
    {
      value: "gig_freelance",
      label: "Gigs",
      icon: <Hammer size={12} />,
    },
    { value: "for_hire", label: "For hire", icon: <Hand size={12} /> },
  ];

export function CategoryToggle() {
  const { filters, setFilter } = useFilterState();

  const toggle = (cat: PostCategory) => {
    const current = filters.categories;
    const next = current.includes(cat)
      ? current.filter((c) => c !== cat)
      : [...current, cat];
    // Don't allow empty — fall back to hiring.
    if (next.length === 0) {
      setFilter("categories", ["hiring"]);
    } else {
      setFilter("categories", next);
    }
  };

  return (
    <div className="inline-flex items-center rounded-md border border-line bg-white p-0.5">
      {OPTIONS.map((opt) => {
        const active = filters.categories.includes(opt.value);
        return (
          <button
            key={opt.value}
            onClick={() => toggle(opt.value)}
            title={
              opt.value === "for_hire"
                ? "People advertising themselves for work"
                : opt.value === "gig_freelance"
                  ? "Small one-off gigs and freelance projects"
                  : "Companies hiring for open roles"
            }
            className={clsx(
              "inline-flex items-center gap-1 text-[11.5px] font-medium px-2 py-1 rounded transition-colors",
              active
                ? "bg-chipBlue text-accent"
                : "text-muted hover:text-ink hover:bg-slate-50",
            )}
          >
            {opt.icon}
            <span>{opt.label}</span>
          </button>
        );
      })}
    </div>
  );
}
