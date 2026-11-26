# open-revoke/deploy/helm/open-revoke/templates/

Each manifest starts with a comment naming the `compose.yaml` service it mirrors and why it differs. Resource names come from `open-revoke.component` (`<fullname>-<component>`), labels from `open-revoke.componentLabels`; every pod uses `open-revoke.podDefaults` and `open-revoke.scheduling`.

- `_helpers.tpl`: shared defines: names and labels, `open-revoke.image` (tag defaults to `appVersion`), `open-revoke.secretName`, `open-revoke.publicUrl` (`publicUrl`, else ingress host, else `http://localhost:18410`), `open-revoke.db.*` (bundled PostgreSQL or `externalDatabase`), `open-revoke.temporalDbEnv`, `open-revoke.podDefaults` (no service account token, no service links).
- `app.yaml`: Service (panel port `http`, in-cluster `api` port for the browser pod) and Deployment of the `app` image (API, worker, panel), one replica, `Recreate`: the entrypoint migrates under an advisory lock, no migration job. Init container `temporal-namespace` creates the namespace. Sets all app env vars, `ALLOWED_HOSTS` from the Service names plus `app.allowedHosts`; `checksum/secret` restarts the pod on a secret change.
- `browser.yaml`: Service (CDP 9223, noVNC 6080, cluster only) and StatefulSet of the browser image with PVC `profile` (signed-in admin sessions) and `/dev/shm` in memory.
- `networkpolicy.yaml`: only app pods reach the browser pod's CDP and noVNC; egress open (`networkPolicy.enabled`).
- `ingress.yaml`: Ingress to the panel port only (`ingress.host` required, optional TLS); the API and live view go through the panel.
- `postgresql.yaml`: Service and StatefulSet of the bundled PostgreSQL with a data PVC; skipped when `postgresql.enabled` is false.
- `redis.yaml`: Service and Deployment of Redis, no persistence.
- `temporal.yaml`: ConfigMap (scripts and dynamic config from `files/temporal/`), Service and Deployment of the Temporal server. Init containers wait for PostgreSQL and create or update the schemas at every start; not Helm hook Jobs, because `helm install --wait` and Argo CD would deadlock on them.
- `secret.yaml`: Secret with `OPEN_REVOKE_SECRET_KEY` and `POSTGRES_PASSWORD`, generated once and kept on upgrade through `lookup`, `helm.sh/resource-policy: keep`; none with `secrets.existingSecret`.
- `NOTES.txt`: post-install text: wait for rollout, panel address or port-forward, `python -m app.cli setup-link`, back up the secret, upgrade command.
