"use client";

import { usePathname } from "next/navigation";
import { ViewTransition } from "react";

/**
 * Animates every page change as a view transition: the old page fades out,
 * the new one settles in (`page-exit`, `page-enter` in `globals.css`); the
 * sidebar stays still. Mounted in `AdminLayout` around the whole page
 * outlet and keyed by the pathname: a `template.tsx` remounts only when its
 * own segment changes (`/people` to `/people/<id>` did not animate), and
 * Next keeps a left route hidden instead of unmounting it, so an exit never
 * ran there. Query string changes (tabs, filters) keep the key and do not
 * animate.
 */
export function PageTransition({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <ViewTransition key={pathname} enter="page-enter" exit="page-exit" default="none">
      <div className="flex min-h-0 flex-1 flex-col">{children}</div>
    </ViewTransition>
  );
}
