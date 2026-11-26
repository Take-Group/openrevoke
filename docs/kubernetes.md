# Kubernetes (Helm)

The Helm chart runs the same images and services as `compose.yaml`, on a Kubernetes cluster.
On one server, the installer and the `open-revoke` command (README, "Get started") do more for
you: backups before updates, automatic rollback, `doctor`. Use the chart when your company runs
its services on Kubernetes.

The chart is published with every release as `oci://ghcr.io/take-group/charts/open-revoke`
(Helm 3.8 or newer), signed with cosign, and attached to the GitHub Release as a `.tgz`. Its
version is the version of Open Revoke. Source: `deploy/helm/open-revoke/`.

Open Revoke holds signed-in admin sessions of your SaaS tools (the browser's PVC) and connector
secrets (the database, encrypted with `OPEN_REVOKE_SECRET_KEY`). Treat the namespace like a
password manager: few people with `exec`, `port-forward` or Secret access.

## What it installs

| Component | Kubernetes | Service in `compose.yaml` |
|---|---|---|
| API, worker and panel | `Deployment` `<release>-app`, 1 replica, `Recreate`; ports 3000 (panel) and 8000 (API, in the cluster only) | `app` |
| Shared Chromium | `StatefulSet` `<release>-browser`, PVC `profile` (5Gi), `/dev/shm` in memory (1Gi) | `browser` |
| PostgreSQL 18 | `StatefulSet` `<release>-postgresql`, PVC `data` (10Gi); off for an external database | `postgres` |
| Redis | `Deployment`, no persistence | `redis` |
| Temporal | `Deployment` `<release>-temporal`; init containers wait for PostgreSQL and set up its schema | `temporal`, `temporal-schema-setup` |
| Temporal namespace | init container of the app pod | `temporal-create-namespace` |
| Secrets | `Secret` `<release>` with `OPEN_REVOKE_SECRET_KEY` and `POSTGRES_PASSWORD` | `.env` |
| Way in | optional `Ingress` to the panel | `caddy` |
| Network | `NetworkPolicy`: only the app pods reach the browser | no published browser port |

`<release>` above is `<release name>-open-revoke`, or the release name alone when it already
contains `open-revoke` (as in the examples below). Database migrations run when the app starts,
under a PostgreSQL lock: there is no migration job.

Requirements: Kubernetes 1.27 or newer, a default StorageClass (or `storageClass` values), about
2 CPU and 4 GiB of memory free. The images are amd64 and arm64.

## Install

```bash
helm install open-revoke oci://ghcr.io/take-group/charts/open-revoke \
  --version X.Y.Z --namespace open-revoke --create-namespace
kubectl -n open-revoke rollout status deploy/open-revoke-app --timeout 10m
```

The first start takes a few minutes: PostgreSQL, Temporal's schema, then the app's migrations.
The chart generates `OPEN_REVOKE_SECRET_KEY` and the database password once and keeps them on
every upgrade. Copy the key into your password manager:

```bash
kubectl -n open-revoke get secret open-revoke -o jsonpath='{.data.OPEN_REVOKE_SECRET_KEY}' | base64 -d
```

Open the panel without an ingress:

```bash
kubectl -n open-revoke port-forward svc/open-revoke-app 18410:3000
```

Then create the first admin with a setup link. Only the link printed on the server creates it; a
new link makes the old one invalid:

```bash
kubectl -n open-revoke exec deploy/open-revoke-app -c app -- python -m app.cli setup-link
```

The setup asks for the organization, the admin account and 2FA; everyone after the first admin
needs an invite.

## Values

Keep your values in a file and pass it to every `helm install` and `helm upgrade`
(`-f values.yaml`). All of them, with comments: `deploy/helm/open-revoke/values.yaml`;
`values.schema.json` refuses unknown keys and wrong types.

```yaml
# values.yaml: a public address with cert-manager
ingress:
  enabled: true
  className: nginx
  host: revoke.example.com
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt
  tls:
    enabled: true
    secretName: open-revoke-tls
timezone: Europe/Warsaw
```

| Value | Default | What it sets |
|---|---|---|
| `publicUrl` | from `ingress.host`, else `http://localhost:18410` | `PUBLIC_URL`: links, cookies, Google sign-in, host names the API answers to |
| `ingress.*` | off | `Ingress` to the panel; `tls.enabled` makes the public URL https |
| `timezone` | `UTC` | `TZ` of every container |
| `secrets.existingSecret` | empty | your own Secret with `OPEN_REVOKE_SECRET_KEY` and `POSTGRES_PASSWORD` |
| `secrets.secretKey` | generated | the key of an installation you move here (below) |
| `app.updateCheck`, `app.telemetry` | `true` | `OPEN_REVOKE_UPDATE_CHECK`, `OPEN_REVOKE_TELEMETRY` (`TELEMETRY.md`) |
| `app.googleOauthRedirectBase` | empty | `GOOGLE_OAUTH_REDIRECT_BASE` (`docs/self-hosting.md`) |
| `app.allowedHosts` | empty | more host names for `ALLOWED_HOSTS` |
| `app.extraEnv` | empty | any other variable of the app |
| `browser.persistence.size` | `5Gi` | PVC of the browser profile |
| `postgresql.persistence.size` | `10Gi` | PVC of PostgreSQL |
| `*.image.tag` | the chart's version | images; never `latest` |
| `networkPolicy.enabled` | `true` | ingress to the browser pod only from the app pods |

The app's `OPEN_REVOKE_INSTALL_METHOD` is `helm`: the panel's update notice then shows the
`helm upgrade` command instead of `open-revoke update`.

The panel is the only port people need. The API is behind it under `/api`, and the live view of
the shared browser goes through the API to signed-in admins. Do not expose the browser Service:
its CDP has no sign-in. The `NetworkPolicy` needs a network plugin that enforces policies
(Calico, Cilium, most managed clusters); without one it does nothing.

## External database

For RDS, Cloud SQL, CloudNativePG or any PostgreSQL 14 or newer:

```yaml
postgresql:
  enabled: false
externalDatabase:
  host: db.example.internal
  port: 5432
  user: open_revoke
  database: open_revoke
  password: "letters-digits-and-dashes-only"   # or POSTGRES_PASSWORD in secrets.existingSecret
  tls: true                                    # encrypted, without certificate checks
```

Create the database `open_revoke` before the install. The user also needs to create the
databases `temporal` and `temporal_visibility` (Temporal's schema setup does it at the first
start), or create them yourself and give the user ownership. The password goes into the app's
connection URL as it is: use letters, digits, `-` and `_`, or percent-encode it.

## Back up

The database holds everything except the browser sessions; it is useless without
`OPEN_REVOKE_SECRET_KEY` (keep the key apart from the dumps). With the bundled PostgreSQL:

```bash
kubectl -n open-revoke exec open-revoke-postgresql-0 -- \
  pg_dump -U postgres -Fc open_revoke > open-revoke-$(date +%F).dump
```

Restore into an installation of the same version, with the app stopped:

```bash
kubectl -n open-revoke scale deploy/open-revoke-app --replicas 0
kubectl -n open-revoke exec open-revoke-postgresql-0 -- \
  psql -U postgres -d postgres -c "DROP DATABASE IF EXISTS open_revoke WITH (FORCE)"
kubectl -n open-revoke exec open-revoke-postgresql-0 -- createdb -U postgres open_revoke
kubectl -n open-revoke exec -i open-revoke-postgresql-0 -- \
  pg_restore -U postgres -d open_revoke --no-owner < open-revoke-2026-01-31.dump
kubectl -n open-revoke scale deploy/open-revoke-app --replicas 1
```

An external database: use its own backups (snapshots, point-in-time recovery). Volume snapshots
of the browser PVC keep the signed-in sessions; without them admins sign in to the SaaS panels
again.

## Update

Read the release notes first: a `### Breaking` section lists a step to run before the update.
Then back up the database and run:

```bash
helm upgrade open-revoke oci://ghcr.io/take-group/charts/open-revoke \
  --version X.Y.Z --namespace open-revoke -f values.yaml
kubectl -n open-revoke rollout status deploy/open-revoke-app --timeout 10m
```

Temporal updates its schema when its pod starts; the app migrates the database when it starts.
The old app pod stops before the new one starts (`Recreate`), so a few minutes without the panel
are normal. Admins see a notice in the panel when a newer release is out.

## Uninstall

```bash
helm uninstall open-revoke --namespace open-revoke
```

This keeps the data: the PVCs of PostgreSQL and the browser (Kubernetes does not delete the PVCs
of a StatefulSet) and the Secret (resource policy `keep`). A new `helm install` with the same
release name uses them again. To remove everything:

```bash
kubectl -n open-revoke delete pvc -l app.kubernetes.io/instance=open-revoke
kubectl -n open-revoke delete secret open-revoke
```

## Move from Docker Compose

1. On the server: `open-revoke backup`, and copy `OPEN_REVOKE_SECRET_KEY` from `.env`.
2. Install the chart of the same version with `secrets.secretKey` set to that key.
3. Restore the database dump from the backup as in "Back up" above.
4. Sign in to the SaaS panels in the shared browser again (or copy the `browser-profile` volume
   into the browser PVC).

## Limits

- One replica of the app, Temporal and PostgreSQL. The chart is for one installation per
  company, not for high availability.
- No `open-revoke update`, `rollback`, `backup` or `doctor`: Helm and your cluster's tools do
  that work. No automatic rollback: a database a newer version migrated cannot be used by an
  older one, so `helm rollback` needs the backup from before the update.
- The sizes of the PVCs are set at install: Kubernetes does not change the `volumeClaimTemplates`
  of a StatefulSet. Resize the PVC itself if its StorageClass allows it.
- Redis has no persistence, as in Docker Compose: after it restarts, make a new setup link if
  the setup is not done yet.
