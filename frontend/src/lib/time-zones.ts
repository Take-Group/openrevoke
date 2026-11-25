// IANA time zones from the browser. The default is the time zone of this computer.

import type { SearchableGroup } from "@/components/common/searchable-select";

export const FALLBACK_TIME_ZONE = "Europe/Warsaw";

/** Time zone of the computer the browser runs on, e.g. "Europe/Warsaw". */
export function detectTimeZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || FALLBACK_TIME_ZONE;
  } catch {
    return FALLBACK_TIME_ZONE;
  }
}

function allTimeZones(): string[] {
  try {
    const zones = Intl.supportedValuesOf("timeZone");
    return zones.includes("UTC") ? zones : ["UTC", ...zones];
  } catch {
    return [FALLBACK_TIME_ZONE, "UTC"];
  }
}

/** "UTC+01:00" now (it changes with daylight saving time). */
export function utcOffset(zone: string): string {
  try {
    const part = new Intl.DateTimeFormat("en-US", { timeZone: zone, timeZoneName: "longOffset" })
      .formatToParts(new Date())
      .find((item) => item.type === "timeZoneName")?.value;
    return part === "GMT" ? "UTC+00:00" : (part ?? "").replace("GMT", "UTC");
  } catch {
    return "";
  }
}

/** "Europe/Warsaw" -> "Europe / Warsaw". */
export function timeZoneLabel(zone: string): string {
  return zone.replaceAll("_", " ").replaceAll("/", " / ");
}

/** The detected zone first, then all of them. Search matches the name and the offset. */
export function timeZoneGroups(detected: string, current: string): SearchableGroup[] {
  const option = (zone: string) => {
    const offset = utcOffset(zone);
    return { value: zone, label: timeZoneLabel(zone), hint: offset, keywords: [zone, offset] };
  };
  const zones = allTimeZones();
  const all = zones.includes(current) ? zones : [current, ...zones];
  return [
    { heading: "This computer", options: [option(detected)] },
    { heading: "All time zones", options: all.filter((zone) => zone !== detected).map(option) },
  ];
}
