# open-revoke/.github/workflows/

GitHub Actions of the public repository. Every action is pinned to a commit SHA with its version
in a comment. Lint locally
with `actionlint` and `uvx zizmor --offline .github/workflows`. Details: skill
`skills/backend/releases.md`, section "Supply chain".

- `ci.yml`: push to main, pull requests, called by `release.yml`: ruff, `alembic check`, panel lint, typecheck and build, Helm lint and kubeconform, ShellCheck.
- `release.yml`: tag `v*`: prepare, tests (`release-test.yml`), publish (`release-publish.yml`), chart to GHCR, immutable GitHub Release.
- `release-publish.yml`: called by `release.yml` after the tests: multi-arch images by digest, tags and cosign signatures, final release files with SHA256SUMS, GitHub artifact attestations (SLSA L3 provenance) of images and files. Reusable, so the attestations carry its identity.
- `release-test.yml`: called by `release.yml` before anything is pushed: amd64 images, Trivy gate and SARIF, release bundle, fresh install, update and rollback, Helm chart on kind.
- `codeql.yml`: CodeQL for Python, TypeScript and the workflows, `security-and-quality` queries (security plus code quality); exclusions, each with its reason, in `../codeql/codeql-config.yml`.
- `workflow-audit.yml`: zizmor on every change, dependency review on pull requests.
- `scorecard.yml`: OpenSSF Scorecard, published to scorecard.dev (README badge) and the Security tab.
- `chromium-check.yml`: weekly check for a newer Chromium in Debian than the released browser image; opens an issue.
