"use client";

import { Panel } from "@/components/common/panel";
import { AccessRequestsTable } from "@/components/requests/access-requests-table";
import { useAccessRequests } from "@/hooks/use-access-requests";

const LIMIT = 20;

/** The person's access requests (newest 20) under their detail page; hidden while they have none. */
export function PersonRequestsSection({ personId }: { personId: string }) {
  const requests = useAccessRequests({ person_id: personId, limit: LIMIT, offset: 0 });
  const data = requests.data;
  if (!data || data.total === 0) return null;
  return (
    <Panel title="Access requests" meta={data.total} className="mt-6">
      <AccessRequestsTable requests={data.items} rowHref={(request) => `/requests/${request.id}`} showPerson={false} />
    </Panel>
  );
}
