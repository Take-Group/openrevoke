# open-revoke/backend/app/services/google_cloud_setup/

Automatic Google Cloud setup for Connect with Google. The API starts it (`service`), the worker runs it in the shared browser (`runner.run`, called by `app/temporal/google_setup_activities.py`), the panel polls `state`.

- `__init__.py`: docstring only.
- `service.py`: `current`, `start`; API side, only reads and starts.
- `runner.py`: `run`; fixed order: signed-in account, project, Admin SDK API, consent screen, OAuth client, Google consent (admin clicks Allow), then saves connection and starts sync and scan.
- `console.py`: Playwright steps in the Cloud console over CDP (`create_project`, `enable_admin_api`, `configure_consent_screen`, `create_oauth_client`, `await_redirect`); English selectors (`hl=en`), each step is re-runnable; `NeedsSignInError`.
- `state.py`: `SetupState` in Redis (`load`, `save`, `to_out`); one setup per installation.
