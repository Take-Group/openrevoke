# open-revoke/deploy/helm/open-revoke/

Helm chart of the self-hosted product: the same images and services as `compose.yaml`, guide `docs/kubernetes.md`, release in skill `skills/backend/releases.md`. CI runs `helm lint --strict` and `helm template | kubeconform`; the release workflow packages it with the product version and installs and upgrades it on kind.

- `.helmignore`: keeps `AGENTS.md` and `CLAUDE.md` out of the chart (lint and package).
- `Chart.yaml`: chart metadata, `kubeVersion` >=1.27, Artifact Hub annotations (`artifacthub.io/images` lists every image tag; the release writes the versions, the numbers in git only matter for a chart used from git).
- `values.yaml`: every value with the env var it sets: `publicUrl`, `secrets` (`existingSecret`, `secretKey`, `postgresPassword`, `redisPassword`), `app`, `service`, `ingress`, `browser`, `postgresql` (off: `externalDatabase`), `redis`, `temporal`, `networkPolicy`. A new value also goes into `values.schema.json`.
- `values.schema.json`: JSON Schema of the values, `additionalProperties: false` everywhere: an unknown key fails `helm install`; patterns for `publicUrl` and the Fernet `secretKey`.
- `templates/`: own AGENTS.md. One file per compose service plus secret, ingress, network policy.
- `files/`, no map: `temporal/` is a copy of `backend/temporal/` (scripts and dynamic config; Helm reads no file outside the chart). CI fails when the copy differs: change both.
