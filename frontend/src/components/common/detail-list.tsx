import { cn } from "@/lib/utils";

export type DetailRow = [label: string, value: React.ReactNode];

/**
 * Label and value rows (a person's details, the signed-in account). Use
 * `StatStrip` for a few numbers across the top of a detail page instead.
 */
export function DetailList({ rows, framed = true, className }: { rows: DetailRow[]; framed?: boolean; className?: string }) {
  return (
    <dl className={cn("text-sm", framed && "divide-y rounded-lg border border-frame bg-card shadow-card", className)}>
      {rows.map(([label, value]) => (
        <div key={label} className={cn("grid grid-cols-[9rem_1fr] gap-4", framed ? "px-4 py-2.5" : "py-1.5")}>
          <dt className="text-muted-foreground">{label}</dt>
          <dd className="min-w-0 break-words">{value}</dd>
        </div>
      ))}
    </dl>
  );
}
