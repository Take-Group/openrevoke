"use client";

import { useState } from "react";

import { FormField } from "@/components/common/form-field";
import { InlineError } from "@/components/common/notice";
import { Panel } from "@/components/common/panel";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface DecisionFormProps {
  title: string;
  /** One line under the title: what the decision does. */
  description: React.ReactNode;
  approveLabel?: string;
  rejectLabel?: string;
  pending: boolean;
  onDecide: (decision: "approve" | "reject", comment: string | null) => void;
}

/**
 * Approve or Reject on the request's own page, with a comment field: a rejection needs the comment
 * (the person who asked reads it), an approval may have one. No dialog: the page is the form.
 */
export function DecisionForm({ title, description, approveLabel = "Approve", rejectLabel = "Reject", pending, onDecide }: DecisionFormProps) {
  const [comment, setComment] = useState("");
  const [missing, setMissing] = useState(false);
  const text = comment.trim();
  return (
    <Panel
      title={title}
      footer={
        <div className="ml-auto flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={pending}
            onClick={() => {
              if (!text) {
                setMissing(true);
                return;
              }
              onDecide("reject", text);
            }}
          >
            {rejectLabel}
          </Button>
          <Button type="button" size="sm" disabled={pending} onClick={() => onDecide("approve", text || null)}>
            {approveLabel}
          </Button>
        </div>
      }
    >
      <div className="flex flex-col gap-3 p-4">
        <p className="text-sm text-muted-foreground">{description}</p>
        <FormField label="Comment" htmlFor="decision-comment" hint="Required to reject. The person who asked sees it.">
          <Textarea
            id="decision-comment"
            maxLength={2000}
            value={comment}
            onChange={(event) => {
              setComment(event.target.value);
              setMissing(false);
            }}
          />
        </FormField>
        {missing && <InlineError message="Write why you reject it before you click Reject." />}
      </div>
    </Panel>
  );
}
