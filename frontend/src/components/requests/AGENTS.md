# open-revoke/frontend/src/components/requests/

Access requests seen by an admin (`/requests`), plus the parts `me/` and `people/` reuse: table, status badge, facts, timeline, decision form. Feature skill: `skills/backend/access-requests.md`.

- `requests-view.tsx`: `RequestsView`, `/requests`: status segments, app and person filters, Export CSV link (`accessRequestsExportUrl`); hooks `useAccessRequests`, `useApps`.
- `request-detail-view.tsx`: `RequestDetailView`, `/requests/[id]`: facts, admin decision or "Decide for the manager" while it waits for the manager, link to the created action, timeline; hooks `useAccessRequest`, `useDecideAccessRequest`.
- `access-requests-table.tsx`: `AccessRequestsTable`: status, waiting for, why, age; props `rowHref`, `showPerson`.
- `request-parts.tsx`: `RequestStatusBadge`, `waitingText`, `DecisionTimeline`, `RequestFacts`, `FALLBACK_TEXT`, `POLICY_TEXT`.
- `decision-form.tsx`: `DecisionForm`: Approve or Reject on the page with a comment; Reject needs the comment.
