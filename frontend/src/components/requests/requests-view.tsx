"use client";

import { AccessRequestsTable } from "@/components/requests/access-requests-table";
import { PageHeader } from "@/components/common/page-header";

/** /requests: access people asked for, in Slack or on My access. */
export function RequestsView() {
  return (
    <>
      <PageHeader title="Access requests" />
      <AccessRequestsTable />
    </>
  );
}
