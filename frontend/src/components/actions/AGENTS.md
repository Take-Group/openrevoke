# open-revoke/frontend/src/components/actions/

The action queue: create/remove/change-role jobs on app accounts, shown in tabs and approved by an admin. Only `src/app/actions/page.tsx` renders it (`/actions`, `?tab=`, `?batch=`); `action-buttons` also shows in other views through `ActionsTable`.

- `actions-view.tsx`: `ActionsView`, type `ActionsTab` (pending, progress, done, failed, cancelled). Tab to status mapping, paging, `batch_id` filter chip; shows `BatchBar` on the pending tab. Hook `useActions`.
- `actions-table.tsx`: `ActionsTable` (`actions`, `emptyText`): one row per `ActionOut` with verb icon, exact payload (account or e-mail, role), status and next step, error, link to the recipe screenshot ("Where it stopped") and the AI's recipe fixes (note in the tooltip). Links to `/people/[id]`.
- `action-buttons.tsx`: `ActionButtons`: row buttons for the allowed transitions (mirrors `services/actions.py` TRANSITIONS in the backend, keep them equal) and the "..." menu. A failed connector write gets "Retry" and "Do it by hand"; a proposed AI fix "Review fix" (confirm dialog) and "Reject AI fix"; active fixes "Revert AI fix". Hooks `useActionTransition`, `useRecipeFixDecision`.
- `batch-bar.tsx`: `BatchBar`: one row per onboarding/offboarding batch with "Approve all". Hook `useApproveBatch`.
- `reveal-secret-dialog.tsx`: `RevealSecretButton`: "Reveal password" for create actions with `has_secret_result`; the API returns the secret once and deletes it, so the dialog keeps it after refetch. Hook `useRevealSecret`.
