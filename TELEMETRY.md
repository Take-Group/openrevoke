# Telemetry

Open Revoke sends one anonymous event so the team knows how many installations
are set up. Nothing else is collected.

## What is sent

When the first admin finishes the setup (organization and admin account), the
server sends one request:

```http
POST https://openrevoke.com/api/v1/telemetry
Content-Type: application/json

{"event": "setup_completed", "version": "0.5.0"}
```

That is all: no e-mail, no names, no organization name, no host name, no
installation id, nothing about your people, apps or accounts. Like any HTTP
server, the receiving end sees the IP address of the request; it does not
record it. The event is sent once per installation, because the setup runs
once.

Builds without a release number (`dev`, the default when you build from
source) send nothing. A failed request is ignored and never retried.

## Turn it off

In `.env`:

```sh
OPEN_REVOKE_TELEMETRY=false
```

Then `open-revoke restart`. The code is `backend/app/services/telemetry.py`.
