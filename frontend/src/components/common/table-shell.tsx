import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react";

import { Button } from "@/components/ui/button";

interface PagerProps {
  total: number;
  limit: number;
  offset: number;
  onOffsetChange: (offset: number) => void;
}

/** "1–100 of 340" with previous and next; only the total when everything fits. */
export function Pager({ total, limit, offset, onOffsetChange }: PagerProps) {
  if (total <= limit && offset === 0) {
    return <p className="mt-3 px-1 text-xs text-muted-foreground tabular-nums">{total} total</p>;
  }
  const last = Math.min(offset + limit, total);
  return (
    <div className="mt-3 flex items-center justify-between gap-2 px-1 text-xs text-muted-foreground tabular-nums">
      <span>
        {total === 0 ? 0 : offset + 1}–{last} of {total}
      </span>
      <div className="flex gap-1">
        <Button
          variant="outline"
          size="icon-sm"
          aria-label="Previous page"
          disabled={offset === 0}
          onClick={() => onOffsetChange(Math.max(0, offset - limit))}
        >
          <ChevronLeftIcon />
        </Button>
        <Button
          variant="outline"
          size="icon-sm"
          aria-label="Next page"
          disabled={last >= total}
          onClick={() => onOffsetChange(offset + limit)}
        >
          <ChevronRightIcon />
        </Button>
      </div>
    </div>
  );
}
