"use client";

import { AppWindowIcon } from "lucide-react";

import { RoleTag } from "@/components/access-profiles/profile-parts";
import { AppAvatar } from "@/components/common/avatars";
import { ConvertedMoney, ConvertedTotal } from "@/components/common/converted-money";
import { EmptyState } from "@/components/common/empty-state";
import { Notice } from "@/components/common/notice";
import { Panel } from "@/components/common/panel";
import { WriteModeBadge } from "@/components/common/write-mode-badge";
import type { PlannedAction } from "@/lib/api/access-profile-types";
import type { MoneyAmount, OnboardSkipped } from "@/lib/api/types";

const SKIP_LABEL: Record<OnboardSkipped["reason"], string> = {
  has_account: "Has an account",
  action_open: "Already open",
};

function PlannedRow({ item }: { item: PlannedAction }) {
  return (
    <div className="flex items-center gap-3 px-3 py-2">
      <AppAvatar name={item.app.name} slug={item.app.slug} size="sm" />
      <span className="min-w-0 flex-1 leading-tight">
        <span className="block truncate font-medium">{item.app.name}</span>
        <span className="block truncate text-xs text-muted-foreground">From {item.profiles.join(", ")}</span>
      </span>
      <RoleTag role={item.role} />
      <WriteModeBadge mode={item.write_mode} what="create" />
      <ConvertedMoney
        converted={item.monthly_cost_converted}
        original={item.monthly_cost}
        className="w-24 justify-end text-right text-muted-foreground"
      />
    </div>
  );
}

interface AssignmentPreviewProps {
  planned: PlannedAction[];
  skipped: OnboardSkipped[];
  warnings: string[];
  monthlyCost: MoneyAmount[];
  monthlyCostTotal: MoneyAmount | null;
  /** Heading of the list, e.g. the person's name in a bulk preview. */
  title?: React.ReactNode;
}

/** What assigning profiles will create: one row per new account with its role, write mode and seat cost. */
export function AssignmentPreview({ planned, skipped, warnings, monthlyCost, monthlyCostTotal, title }: AssignmentPreviewProps) {
  return (
    <div className="flex flex-col gap-3">
      {warnings.map((warning) => (
        <Notice key={warning} tone="warning">
          {warning}
        </Notice>
      ))}
      <Panel
        title={title ?? "Accounts to create"}
        meta={`${planned.length}`}
        bodyClassName="flex flex-col divide-y text-sm"
        footer={
          <>
            <span>
              {skipped.length > 0 &&
                `Skipped: ${skipped.map((item) => `${item.app.name} (${SKIP_LABEL[item.reason].toLowerCase()})`).join(", ")}`}
            </span>
            <span className="flex items-center gap-2">
              Monthly cost <ConvertedTotal total={monthlyCostTotal} parts={monthlyCost} className="font-medium text-foreground" />
            </span>
          </>
        }
      >
        {planned.length === 0 ? (
          <EmptyState icon={AppWindowIcon} title="Nothing to create: the person has every app" className="py-6" />
        ) : (
          planned.map((item) => <PlannedRow key={item.app.app_id} item={item} />)
        )}
      </Panel>
    </div>
  );
}
