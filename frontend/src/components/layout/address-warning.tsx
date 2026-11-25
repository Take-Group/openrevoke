"use client";

import { useSyncExternalStore } from "react";

import { Notice } from "@/components/common/notice";
import { useAuthState } from "@/hooks/use-auth";

const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "[::1]"]);

function isLocal(hostname: string): boolean {
  return LOCAL_HOSTS.has(hostname) || hostname.endsWith(".localhost");
}

/** What is wrong with the address this page was opened at, or null. */
function problem(publicUrl: string, location: URL): string | null {
  let expected: URL;
  try {
    expected = new URL(publicUrl);
  } catch {
    return `PUBLIC_URL is not a valid address: ${publicUrl}. Fix it in .env and restart.`;
  }
  if (expected.origin !== location.origin) {
    return (
      `You opened Open Revoke at ${location.origin}, but PUBLIC_URL is ${expected.origin}. ` +
      `Invite and reset links and Google sign-in point there. Open the panel at that address, or set PUBLIC_URL in .env to this one and restart.`
    );
  }
  if (location.protocol === "http:" && !isLocal(location.hostname)) {
    return (
      "The panel runs over plain http: passwords and the session cookie cross the network unencrypted, " +
      "and Google sign-in does not work. Put HTTPS in front of it (docs/self-hosting.md)."
    );
  }
  return null;
}

/**
 * Warns when the panel is opened under an address other than PUBLIC_URL, or over http on
 * a non-local host. Like Gitea's ROOT_URL banner: a wrong address breaks invite and reset links
 * and Google sign-in without any error at the time.
 */
const noSubscription = () => () => {};

export function AddressWarning({ className }: { className?: string }) {
  const auth = useAuthState();
  // The page's own address; null while rendering on the server.
  const here = useSyncExternalStore(noSubscription, () => window.location.origin, () => null);
  const publicUrl = auth.data?.public_url;
  const message = publicUrl && here ? problem(publicUrl, new URL(here)) : null;
  if (!message) return null;
  return (
    <Notice tone="warning" className={className}>
      {message}
    </Notice>
  );
}
