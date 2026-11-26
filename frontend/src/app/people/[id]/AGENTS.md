# open-revoke/frontend/src/app/people/[id]/

Routes of one person. Each `page.tsx` awaits `params` and renders one view from `src/components/people/`; the form pages load the person themselves, so their address works when opened directly.

- `page.tsx`: `/people/<id>` renders `PersonDetailView`.
- `edit/`: `/people/<id>/edit` renders `EditPersonView`.
- `add-to-app/`: `/people/<id>/add-to-app` renders `AddToAppView`.
- `onboard/`: `/people/<id>/onboard` renders `OnboardView`.
- `offboard/`: `/people/<id>/offboard` renders `OffboardView`.
- `access-profiles/`: `add/` is `/people/<id>/access-profiles/add` and renders `AssignProfilesView` (from `src/components/access-profiles/`).
