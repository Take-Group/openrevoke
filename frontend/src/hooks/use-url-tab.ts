"use client";

import { useState } from "react";

/**
 * State mirrored in a URL query param (default `?tab=`, e.g. `?step=` for a wizard) so the view
 * can be linked and survives a reload. The page reads the param on the server and passes it as
 * `initial`. `replaceState` changes the URL without a navigation or a history entry; the fallback
 * value drops the param to keep the URL short.
 */
export function useUrlTab<T extends string>(initial: T | undefined, fallback: T, param = "tab"): [T, (tab: T) => void] {
  const [tab, setTab] = useState<T>(initial ?? fallback);

  const select = (next: T) => {
    setTab(next);
    const params = new URLSearchParams(window.location.search);
    if (next === fallback) params.delete(param);
    else params.set(param, next);
    const query = params.toString();
    window.history.replaceState(null, "", `${window.location.pathname}${query ? `?${query}` : ""}`);
  };

  return [tab, select];
}
