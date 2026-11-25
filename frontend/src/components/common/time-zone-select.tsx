"use client";

import { useState } from "react";

import { SearchableSelect } from "@/components/common/searchable-select";
import { detectTimeZone, timeZoneGroups } from "@/lib/time-zones";

interface TimeZoneSelectProps {
  id: string;
  value: string;
  onChange: (zone: string) => void;
  disabled?: boolean;
}

/** All IANA time zones with a search box; this computer's zone on top. */
export function TimeZoneSelect({ id, value, onChange, disabled }: TimeZoneSelectProps) {
  const [detected] = useState(detectTimeZone);
  return (
    <SearchableSelect
      id={id}
      value={value}
      onChange={onChange}
      groups={timeZoneGroups(detected, value)}
      placeholder="Select a time zone"
      searchPlaceholder="Search city or UTC offset"
      emptyText="No such time zone"
      disabled={disabled}
    />
  );
}
