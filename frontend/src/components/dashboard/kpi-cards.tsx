import Link from "next/link";

import { InfoTip } from "@/components/common/info-tip";
import { RatesSource } from "@/components/common/rates-source";
import { StatusDot } from "@/components/common/status-badge";
import { ROW_HOVER } from "@/components/dashboard/row-hover";
import { formatMoney } from "@/lib/format";
import type { Dashboard } from "@/lib/api/types";
import { cn } from "@/lib/utils";

interface KpiProps {
  label: React.ReactNode;
  value: React.ReactNode;
  footer: React.ReactNode;
  href?: string;
}

const CELL = "flex min-w-0 flex-col gap-1 bg-card px-5 py-4";

/** One figure of the strip: small label, the number, one caption line. */
function Kpi({ label, value, footer, href }: KpiProps) {
  const body = (
    <>
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">{label}</div>
      <div className="truncate text-[1.75rem] leading-9 font-medium tracking-[-0.02em] tabular-nums">{value}</div>
      <div className="min-h-4 truncate text-xs text-muted-foreground">{footer}</div>
    </>
  );
  return href ? (
    <Link
      href={href}
      className={cn(CELL, ROW_HOVER)}
    >
      {body}
    </Link>
  ) : (
    <div className={CELL}>{body}</div>
  );
}

function Attention({ count, text, tone }: { count: number; text: string; tone: "warning" | "danger" }) {
  if (count === 0) return null;
  return (
    <span className="inline-flex items-center gap-1.5">
      <StatusDot tone={tone} />
      {count} {text}
    </span>
  );
}

export function KpiCards({ data }: { data: Dashboard }) {
  const { counts } = data;
  const [main, ...other] = data.monthly_cost;
  const total = data.monthly_cost_total;
  const foreign = total ? data.monthly_cost.filter((part) => part.currency !== total.currency) : [];
  const critical = data.alerts.filter((alert) => alert.severity === "critical").length;

  return (
    // The 1px gaps over a border-coloured background draw the hairlines at any column count.
    <div className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-frame bg-border shadow-card xl:grid-cols-4">
      <Kpi
        label="People"
        value={counts.people_active}
        href="/people?status=active"
        footer={`${counts.people_left} left`}
      />
      <Kpi
        label="Accounts"
        value={counts.accounts}
        href="/apps"
        footer={
          <span className="flex flex-wrap gap-x-3">
            <span>{counts.seats} paid seats</span>
            <Attention count={counts.accounts_unassigned} text="without owner" tone="warning" />
          </span>
        }
      />
      <Kpi
        label={
          <>
            Monthly cost
            <InfoTip>
              {total
                ? `All apps in ${total.currency}, converted with the daily exchange rates. Yearly plans count as 1/12.`
                : "Per currency: a currency has no exchange rate, so the amounts are not converted. Yearly plans count as 1/12."}
              {foreign.length > 0 && <div className="mt-1">From: {data.monthly_cost.map(formatMoney).join(" + ")}</div>}
            </InfoTip>
          </>
        }
        value={total ? formatMoney(total) : main ? formatMoney(main) : "—"}
        footer={
          total ? (
            foreign.length > 0 ? (
              <RatesSource info={data.exchange_rates} />
            ) : (
              `${counts.apps} apps`
            )
          ) : other.length > 0 ? (
            other.map(formatMoney).join(" · ")
          ) : (
            `${counts.apps} apps`
          )
        }
      />
      <Kpi
        label="Alerts"
        value={data.alerts.length}
        href="#alerts"
        footer={
          <span className="flex flex-wrap gap-x-3">
            {critical === 0 && counts.actions_pending_approval === 0 && "Nothing urgent"}
            <Attention count={critical} text="critical" tone="danger" />
            <Attention count={counts.actions_pending_approval} text="to approve" tone="warning" />
          </span>
        }
      />
    </div>
  );
}
