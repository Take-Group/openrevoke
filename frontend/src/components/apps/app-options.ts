import type { SelectOption } from "@/components/common/option-select";
import type { ConnectorOut, Integration, PricingModel } from "@/lib/api/types";

export const PRICING_OPTIONS: { value: PricingModel; label: string }[] = [
  { value: "per_seat", label: "Per seat" },
  { value: "flat", label: "Flat" },
  { value: "free", label: "Free" },
];

export const BILLING_OPTIONS: SelectOption[] = [
  { value: "monthly", label: "Monthly" },
  { value: "yearly", label: "Yearly" },
];

/** Which integration a connector implies, from its auth kind. */
export function integrationOfConnector(connector: Pick<ConnectorOut, "auth_kind">): Integration {
  switch (connector.auth_kind) {
    case "browser_session":
      return "browser";
    case "scim_token":
      return "scim";
    default:
      return "api";
  }
}
