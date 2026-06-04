export function ChartCard({
  title,
  subtitle,
  children,
  height = 280,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  height?: number;
}) {
  return (
    <section className="bg-white border border-line rounded-xl shadow-card p-4 sm:p-5">
      <div className="mb-3">
        <h3 className="text-[11px] font-bold uppercase tracking-wider text-muted">
          {title}
        </h3>
        {subtitle && (
          <p className="text-xs text-soft mt-1">{subtitle}</p>
        )}
      </div>
      <div style={{ height }}>{children}</div>
    </section>
  );
}
