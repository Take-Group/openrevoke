# open-revoke/backend/app/connectors/fake/

The `fake` connector: development data with no network (API token auth, domain-bound), listed only in development. Reads are deterministic; writes live in Redis so verification and the next sync see them.

- `__init__.py`: empty.
- `connector.py`: `FakeConnector(Connector, AppDiscovery)`, `FakeConfig`; supports list, create, delete, people and app discovery; `target_fields = ("domain",)`.
- `mapping.py`: `fake_accounts(domain, count)` (users plus one service account without e-mail), `fake_people` (two-level org chart with departments and titles; `manager@` heads Engineering, `member@` works there, matching the dev panel users), `created_account`.
- `state.py`: `apply_state`, `add_created`, `mark_deleted` over Redis keys `open-revoke:fake-connector:*` per domain.
- `discovery.py`: `fake_discovery(domain, count, since, until)`: fictional sign-ins (Fake Notes, Fake Design, Fake Video, Fake Chat) and a deleted `former@` user.
