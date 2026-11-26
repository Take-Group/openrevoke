# Telemetry

Open Revoke sends one anonymous event so the team knows how many installations
are set up. Nothing else is collected. The hourly update check (below) asks GitHub, not us.

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

## Update check (not telemetry, its own switch)

Once an hour (with up to 30 minutes of random delay) and at every start, the server asks GitHub
for the latest stable release, so the panel can tell admins when a newer version is out:

```http
GET https://api.github.com/repos/Take-Group/openrevoke/releases/latest
```

Nothing goes to the Open Revoke team. GitHub sees what any HTTP request shows: the IP address of
your server and the header `User-Agent: open-revoke/<version>` (the version you run). No
installation id, host name or data about your people and apps is sent. Builds
without a release number (`dev`) do not check. Turn it off (servers without internet access, or
when you watch releases yourself) in `.env`:

```sh
OPEN_REVOKE_UPDATE_CHECK=false
```

Then `open-revoke restart`; in the Helm chart `app.updateCheck: false`. The code is
`backend/app/services/update_check.py`.
