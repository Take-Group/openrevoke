# Open Revoke Frontend

The Open Revoke panel: Next.js, React, TypeScript, Tailwind CSS and Bun.

## Running in development

The dev stack is `../compose.dev.yaml` (`dc` below = `docker compose -f compose.dev.yaml`
in the repository folder). The panel runs in it as the `web` service under `next dev`, with the code
mounted from disk: a change in `src/` or `public/` needs no rebuild.

- Panel: http://localhost:18410
- API: http://localhost:18411

Checks:

```bash
dc exec web bun run lint
dc exec web bun run typecheck
dc logs --tail 100 web
```

## Self-hosting

The production image (`next build`, no hot reload) starts together with the backend
from the `open-revoke/` folder: `docker compose up -d --build`, panel at
http://localhost:18410. Details: `../README.md`.
