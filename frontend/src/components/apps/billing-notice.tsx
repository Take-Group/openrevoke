"use client";

import { ReceiptTextIcon } from "lucide-react";

import { Notice } from "@/components/common/notice";
import { Button } from "@/components/ui/button";
import { useUpdateApp } from "@/hooks/use-apps";
import { formatDateTime } from "@/lib/date-time";
import { formatMoney, formatRelative } from "@/lib/format";
import type { AppBillingOut } from "@/lib/api/billing-types";
import type { AppDetail } from "@/lib/api/types";

const PERIOD = { monthly: "month", yearly: "year" } as const;

function summary(billing: AppBillingOut): string {
  const period = PERIOD[billing.billing_period];
  const unit = formatMoney({ amount: billing.unit_amount, currency: billing.currency });
  const parts = [
    billing.plan ? `${billing.plan} plan` : null,
    billing.pricing_model === "per_seat" ? `${unit} per seat / ${period}` : `${unit} / ${period}`,
    billing.billed_seats !== null ? `${billing.billed_seats} billed seats` : null,
    billing.total_amount !== null
      ? `${formatMoney({ amount: billing.total_amount, currency: billing.currency })} / ${period} in total`
      : null,
    billing.renews_on ? `renews ${formatDateTime(billing.renews_on, { dateStyle: "medium" })}` : null,
  ];
  return parts.filter(Boolean).join(" · ");
}

/** The price the app's own billing reports, and whether the app's price follows it. */
export function BillingNotice({ app, onApplied }: { app: AppDetail; onApplied: (app: AppDetail) => void }) {
  const update = useUpdateApp(app.id);
  const billing = app.billing;
  if (!billing) return null;
  const follows = billing.applies_to_price;
  return (
    <Notice
      icon={ReceiptTextIcon}
      title={follows ? `Price read from ${app.name} billing` : `${app.name} billing differs from the price below`}
      action={
        follows ? undefined : (
          <Button
            variant="outline"
            size="sm"
            disabled={update.isPending}
            onClick={() => update.mutate({ price_from_app: true }, { onSuccess: onApplied })}
          >
            Use billing price
          </Button>
        )
      }
    >
      <p>{summary(billing)}</p>
      <p className="text-xs">
        Read {formatRelative(billing.read_at)} by the sync.{" "}
        {follows
          ? "Each sync updates the price. Changing it below stops that."
          : "The price below was set by hand, so syncs leave it."}
      </p>
    </Notice>
  );
}
