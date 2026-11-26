"use client";

import { DetailPageSkeleton } from "@/components/common/page-skeletons";
import { PageHeader } from "@/components/common/page-header";
import { QueryState } from "@/components/common/query-state";
import { Notice } from "@/components/common/notice";
import { TextLink } from "@/components/common/links";
import { DecisionForm } from "@/components/requests/decision-form";
import { DecisionTimeline, RequestFacts } from "@/components/requests/request-parts";
import { useAccessRequest, useDecideAccessRequest } from "@/hooks/use-access-requests";
import { fullName } from "@/lib/format";
import type { AccessRequestDetail } from "@/lib/api/access-request-types";
import type { ActionStatus } from "@/lib/api/types";

function actionTab(status: ActionStatus): string {
  if (status === "pending_approval") return "pending";
  if (status === "done" || status === "failed" || status === "cancelled") return status;
  return "progress";
}

function AdminDecision({ request }: { request: AccessRequestDetail }) {
  const approve = useDecideAccessRequest(request.id, "approve");
  const reject = useDecideAccessRequest(request.id, "reject");
  const pending = approve.isPending || reject.isPending;
  const decide = (decision: "approve" | "reject", comment: string | null) =>
    (decision === "approve" ? approve : reject).mutate({ comment });
  if (request.status === "pending_manager") {
    const manager = request.approver ? fullName(request.approver) : "the manager";
    return (
      <DecisionForm
        title="Decide for the manager"
        description={`The request waits for ${manager}. Your decision is recorded as an admin decision for the manager.`}
        approveLabel="Approve for the manager"
        rejectLabel="Reject for the manager"
        pending={pending}
        onDecide={decide}
      />
    );
  }
  if (request.status === "pending_admin") {
    return (
      <DecisionForm
        title="Admin decision"
        description="Approving starts the account creation (a manual task when the app has no connector)."
        pending={pending}
        onDecide={decide}
      />
    );
  }
  return null;
}

/** `/requests/[id]`: one access request, its decision timeline and the admin's Approve / Reject. */
export function RequestDetailView({ id }: { id: string }) {
  const request = useAccessRequest(id);
  return (
    <>
      <PageHeader title="Access request" back={{ href: "/requests", label: "Requests" }} />
      <QueryState query={request} feature="Access request" loading={<DetailPageSkeleton stats={0} tabs={0} />}>
        {(data) => (
          <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
            <RequestFacts request={data} admin />
            {data.action && (
              <Notice tone="info">
                The request&apos;s account action is <TextLink href={`/actions?tab=${actionTab(data.action.status)}`}>in Actions</TextLink>.
              </Notice>
            )}
            <AdminDecision request={data} />
            <DecisionTimeline request={data} />
          </div>
        )}
      </QueryState>
    </>
  );
}
