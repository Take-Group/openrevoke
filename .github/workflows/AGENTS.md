# open-revoke/.github/workflows/

GitHub Actions of the public repository. Every action is pinned to a commit SHA with its version
in a comment; the `slsa-github-generator` workflows are the one exception (by tag). Lint locally
with `actionlint` and `uvx zizmor --offline .github/workflows`. Details: skill
`skills/backend/releases.md`, section "Supply chain".

- `ci.yml`: push to main, pull requests, called by `release.yml`: ruff, `alembic check`, panel lint, typecheck and build, Helm lint and kubeconform, ShellCheck.
- `release.yml`: tag `v*`: prepare, publish multi-arch images by digest, tag and cosign-sign, SLSA L3 provenance (images and files), chart to GHCR, immutable GitHub Release.
- `release-test.yml`: called by `release.yml` before anything is pushed: amd64 images, Trivy gate and SARIF, release bundle, fresh install, update and rollback, Helm chart on kind.
- `codeql.yml`: CodeQL for Python, TypeScript and the workflows, `security-extended` queries.
- `workflow-audit.yml`: zizmor on every change, dependency review on pull requests.
- `scorecard.yml`: OpenSSF Scorecard, published to scorecard.dev (README badge) and the Security tab.
- `chromium-check.yml`: weekly check for a newer Chromium in Debian than the released browser image; opens an issue.
