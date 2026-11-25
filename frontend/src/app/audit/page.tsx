import type { Metadata } from "next";

import { AuditView } from "@/components/audit/audit-view";

export const metadata: Metadata = { title: "Audit" };

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function uuid(value: string | undefined): string | undefined {
  return value && UUID.test(value) ? value : undefined;
}

/** `?entity=<type>&id=<uuid>`: one entity. `?app=<uuid>` or `?person=<uuid>`: everything about an app or a person. */
export default async function AuditPage({
  searchParams,
}: {
  searchParams: Promise<{ entity?: string; id?: string; app?: string; person?: string }>;
}) {
  const { entity, id, app, person } = await searchParams;
  return (
    <AuditView
      key={`${entity}-${id}-${app}-${person}`}
      initialEntityType={entity}
      entityId={uuid(id)}
      appId={uuid(app)}
      personId={uuid(person)}
    />
  );
}
