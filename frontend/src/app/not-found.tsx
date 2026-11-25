import Link from "next/link";
import { CompassIcon } from "lucide-react";

import { EmptyState } from "@/components/common/empty-state";
import { buttonVariants } from "@/components/ui/button";

export default function NotFound() {
  return (
    <EmptyState
      icon={CompassIcon}
      title="Page not found"
      className="py-24"
      action={
        <Link href="/" className={buttonVariants({ variant: "outline" })}>
          Dashboard
        </Link>
      }
    />
  );
}
