# Open Revoke frontend (panel)

Product rules are in `../AGENTS.md`.

## Stack

| Layer | Technology |
| --- | --- |
| Runtime | Bun |
| Framework | Next.js 16 (App Router, `output: "standalone"`) |
| Language | TypeScript 6 |
| UI | React 19, Base UI, shadcn/ui 4 |
| Styles | Tailwind CSS 4, tw-animate-css, CVA |
| State / fetch | TanStack React Query 5 |
| Icons | Lucide React |
| Lint | ESLint 9 (eslint-config-next) |

## Running

The local stack runs the panel as service `web` with `next dev` and the code
mounted, so changes show up at once with hot reload:
http://localhost:18410. A new package: `bun add <pkg>` on the
host in `frontend/`, then `dc restart web` (node_modules live in a volume).
Never start `bun run dev` on the host next to the stack.

The browser calls the API on the panel origin (`/api/...`); Next.js proxies it
to `API_PROXY_TARGET` (the `api` container in the local stack, the API
process in the same container in the self-hosting image). Details:
[skills/frontend/api-communication.md](../skills/frontend/api-communication.md);
pages and hooks: [skills/frontend/pages.md](../skills/frontend/pages.md).

API types (`src/lib/api/types.ts`) are written by hand from
`../docs/openapi.json`. After a contract change, update them in the same change.

The self-hosting image builds the panel with `next build` (Dockerfile target
`app`, served by `bun server.js` under supervisor).

## Checks

```bash
dc exec web bun run lint
dc exec web bun run typecheck
# then open http://localhost:18410/people (sign in first)
```

No automated tests and no test frameworks. Check the page by hand in the
running stack.

## Files

- `.dockerignore`, `.gitignore`: build context and git filters (`node_modules`, `.next`).
- `README.md`: dev quick start for the panel.
- `bun.lock`, `package.json`: dependencies and scripts `dev`, `build`, `start`, `lint`, `typecheck`.
- `components.json`: shadcn config (style `base-nova`, aliases `@/components`, `@/lib`, `@/hooks`, CSS in `src/app/globals.css`).
- `eslint.config.mjs`: ESLint 9 (next config) plus the UI kit rules (`no-restricted-syntax`: raw controls, `onClick` on non-interactive elements, palette colours, `cursor-default`; `ui/` and `common/` get only the colour and cursor rules).
- `postcss.config.mjs`, `tsconfig.json`: Tailwind 4 PostCSS plugin, TypeScript with `@/*` alias to `src/`.
- `next.config.ts`: `output: "standalone"`, rewrites `/api/:path*` and `/mcp` to `API_PROXY_TARGET` (default `http://127.0.0.1:8000`, baked in at build time), `allowedDevOrigins` `*.localhost`.
- `public/`, no map: default Next.js SVGs `file.svg`, `globe.svg`, `next.svg`, `vercel.svg`, `window.svg`; nothing in the panel depends on them.
- `src/`, no map: `src/app/` (own AGENTS.md: routes), `src/components/` (own AGENTS.md: UI by feature plus the `ui` and `common` kits), `src/hooks/` (own AGENTS.md: React Query hooks, one file per API resource), `src/lib/` (own AGENTS.md: helpers, API client and types).

## Code rules

- Build every screen from the shared components in `src/components/ui/`
  and `src/components/common/`; read
  [skills/frontend/ui-kit.md](../skills/frontend/ui-kit.md) first. No raw
  `<button>`, `<input>`, `<select>`, `<textarea>`, `<datalist>`: the
  browser draws them in its own style. A missing component goes to
  `common/` and into the catalogue, never inline in a page.
- Anything clickable is a kit component with all four states: pointer
  cursor, hover, keyboard focus ring, disabled (`cursor-not-allowed`). No
  `onClick` on a `div` or `span`, never `cursor-default`. Colours are tokens
  only (violet accent `brand`), never `bg-blue-500` or hex.
- `bun run lint` enforces these rules (`eslint.config.mjs`); its message
  names the component to use. Fix the code, never `eslint-disable` it.
- SOLID: one job per component, hook and module; extend through props and
  composition; components use hooks and providers, not services directly.
- Max 600 lines per file.

### Next.js 16

<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
