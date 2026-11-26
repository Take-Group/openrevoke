"use client";

import { DetailPageSkeleton } from "@/components/common/page-skeletons";
import { PageHeader } from "@/components/common/page-header";
import { QueryState } from "@/components/common/query-state";
import { DecisionForm } from "@/components/requests/decision-form";
import { DecisionTimeline, RequestFacts } from "@/components/requests/request-parts";
import { useDecideMyApproval, useMyApproval } from "@/hooks/use-me";
import type { AccessRequestDetail } from "@/lib/api/access-request-types";

function ManagerDecision({ request }: { request: AccessRequestDetail }) {
  const approve = useDecideMyApproval(request.id, "approve");
  const reject = useDecideMyApproval(request.id, "reject");
  if (request.status !== "pending_manager") return null;
  const next =
    request.policy === "manager_then_admin" ? "After your yes an admin approves it too." : "Your yes creates the account.";
  return (
    <DecisionForm
      title="Your decision"
      description={`You decide as the manager. ${next}`}
      pending={approve.isPending || reject.isPending}
      onDecide={(decision, comment) => (decision === "approve" ? approve : reject).mutate({ comment })}
    />
  );
}

/** `/me/approvals/[id]`: who asks for what and why, the seat cost, Approve and Reject with a comment. */
export function ApprovalDetailView({ id }: { id: string }) {
  const request = useMyApproval(id);
  return (
    <>
      <PageHeader title="Access request" back={{ href: "/me/approvals", label: "Approvals" }} />
      <QueryState query={request} feature="Access request" loading={<DetailPageSkeleton stats={0} tabs={0} />}>
        {(data) => (
          <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
            <RequestFacts request={data} />
            <ManagerDecision request={data} />
            <DecisionTimeline request={data} />
          </div>
        )}
      </QueryState>
    </>
  );
}
