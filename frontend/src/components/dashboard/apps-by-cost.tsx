"use client";

import Link from "next/link";
import { AppWindowIcon } from "lucide-react";

import { AppAvatar } from "@/components/common/avatars";
import { EmptyState } from "@/components/common/empty-state";
import { InfoTip } from "@/components/common/info-tip";
import { Panel } from "@/components/common/panel";
import { ROW_HOVER } from "@/components/dashboard/row-hover";
import { buttonVariants } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { useApps } from "@/hooks/use-apps";
import { amountOf, formatMoney } from "@/lib/format";
import type { AppListItem, MoneyAmount } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const TOP = 7;

/** With a converted total: the share of the total in the organization currency. */
function topConverted(apps: AppListItem[], total: MoneyAmount): Row[] {
  const sum = amountOf(total) || 1;
  return apps
    .filter((app) => app.monthly_cost_converted && amountOf(app.monthly_cost_converted) > 0)
    .map((app) => ({ app, money: app.monthly_cost_converted!, share: amountOf(app.monthly_cost_converted) / sum }))
    .sort((a, b) => b.share - a.share)
    .slice(0, TOP);
}

interface Row {
  app: AppListItem;
  money: MoneyAmount;
  share: number;
}

/**
 * Without a converted total (a currency has no rate): the share of the total
 * in the app's own currency.
 */
function topApps(apps: AppListItem[], totals: MoneyAmount[]): Row[] {
  const total = new Map(totals.map((money) => [money.currency, amountOf(money)]));
  // The dashboard lists the biggest currency first: keep that order, then the biggest app first.
  const order = new Map(totals.map((money, index) => [money.currency, index]));
  return apps
    .filter((app) => app.monthly_cost && amountOf(app.monthly_cost) > 0)
    .map((app) => ({
      app,
      money: app.monthly_cost!,
      share: amountOf(app.monthly_cost) / (total.get(app.monthly_cost!.currency) || 1),
    }))
    .sort(
      (a, b) =>
        (order.get(a.app.monthly_cost!.currency) ?? 99) - (order.get(b.app.monthly_cost!.currency) ?? 99) ||
        b.share - a.share,
    )
    .slice(0, TOP);
}

export function AppsByCost({ totals, total }: { totals: MoneyAmount[]; total: MoneyAmount | null }) {
  const apps = useApps({ limit: 500 });
  const items = apps.data?.items ?? [];
  const rows = total ? topConverted(items, total) : topApps(items, totals);

  return (
    <Panel
      className="h-full"
      title={
        <>
          Cost by app
          <InfoTip>
            {total ? `Share of the monthly total in ${total.currency}.` : "Share of the monthly total in the same currency."}
          </InfoTip>
        </>
      }
    >
      {apps.isSuccess && rows.length === 0 ? (
        <EmptyState
          icon={AppWindowIcon}
          title="No costs yet"
          action={
            <Link href="/apps" className={buttonVariants({ variant: "outline", size: "sm" })}>
              Open apps
            </Link>
          }
        />
      ) : (
        <ul className="flex flex-col py-1.5">
          {rows.map(({ app, money, share }) => (
            <li key={app.id}>
              <Link
                href={`/apps/${app.id}`}
                className={cn("flex items-center gap-3 px-4 py-2 text-sm", ROW_HOVER)}
              >
                <AppAvatar name={app.name} slug={app.slug} connectorKey={app.connector_key} size="sm" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="truncate">{app.name}</span>
                    <span className="shrink-0 tabular-nums">
                      {formatMoney(money)}
                      <span className="ml-2 inline-block w-9 text-right text-xs text-muted-foreground">
                        {Math.round(share * 100)}%
                      </span>
                    </span>
                  </div>
                  <Progress value={Math.max(share * 100, 2)} aria-label={`Share of ${app.name}`} className="mt-1.5" />
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
