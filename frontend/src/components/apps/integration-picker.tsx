"use client";

import { INTEGRATION } from "@/components/common/integration-icon";
import { Segmented } from "@/components/common/segmented";
import type { Integration } from "@/lib/api/types";

const ORDER: Integration[] = ["manual", "api", "scim", "browser"];

/** Integration type as a segmented control with icons. */
export function IntegrationPicker({ value, onChange }: { value: Integration; onChange: (value: Integration) => void }) {
  return (
    <Segmented
      label="Integration"
      value={value}
      onChange={onChange}
      className="w-full [&>*]:flex-1"
      options={ORDER.map((key) => {
        const { icon: Icon, label } = INTEGRATION[key];
        return {
          value: key,
          label: (
            <>
              <Icon />
              {label}
            </>
          ),
        };
      })}
    />
  );
}
