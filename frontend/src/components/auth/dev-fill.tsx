"use client";

import { WandSparklesIcon } from "lucide-react";
import { useRef } from "react";
import { createPortal, flushSync } from "react-dom";

import { Button } from "@/components/ui/button";
import { useAuthState } from "@/hooks/use-auth";
import type { DevPrefill } from "@/lib/api/auth-types";

/** Test values for the sign-in forms, only when the API runs with OPEN_REVOKE_DEV_PREFILL. */
export function useDevPrefill(): DevPrefill | null {
  return useAuthState().data?.dev_prefill ?? null;
}

/** A fresh address per click (`new.user+k3x9@example.com`), so every test sign-up is a new account. */
export function uniqueEmail(email: string): string {
  const [local, domain] = email.split("@");
  return `${local}+${Date.now().toString(36)}@${domain}`;
}

/**
 * Development only: a small pill in the bottom left corner of the screen (outside the card, so the
 * form looks as in production) that fills the form it is placed in with `dev_prefill` and submits
 * it. Renders nothing without `dev_prefill`.
 */
export function DevFillButton({ onFill }: { onFill: (prefill: DevPrefill) => void }) {
  const prefill = useDevPrefill();
  const anchor = useRef<HTMLSpanElement>(null);
  if (!prefill) return null;

  const fillAndSubmit = () => {
    flushSync(() => onFill(prefill)); // the inputs hold the values before the submit reads them
    anchor.current?.closest("form")?.requestSubmit();
  };

  return (
    <>
      {/* Marks the form to submit; the pill itself lives in <body>. */}
      <span ref={anchor} hidden />
      {createPortal(
        <Button
          type="button"
          variant="outline"
          size="xs"
          className="fixed bottom-4 left-4 z-50 border-dashed bg-card text-muted-foreground shadow-card"
          onClick={fillAndSubmit}
        >
          <WandSparklesIcon />
          Dev fill
        </Button>,
        document.body,
      )}
    </>
  );
}
