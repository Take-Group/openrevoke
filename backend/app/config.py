from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_name: str = "Open Revoke"
    debug: bool = False
    # Time zone of the server (logs, container clocks). install.sh copies it from the host;
    # dates in the panel use the organization's time zone instead.
    timezone: str = Field(default="UTC", validation_alias="TZ")

    # Version of this build: the release image sets it from the git tag (Dockerfile
    # ARG OPEN_REVOKE_VERSION); the local stack runs "dev". skills/backend/releases.md.
    version: str = Field(default="dev", validation_alias="OPEN_REVOKE_VERSION")
    # Hourly check of the public GitHub repository for a newer stable release
    # (skills/backend/releases.md). Off for servers without internet access.
    update_check: bool = Field(default=True, validation_alias="OPEN_REVOKE_UPDATE_CHECK")
    update_check_url: str = Field(
        default="https://api.github.com/repos/Take-Group/openrevoke/releases/latest",
        validation_alias="OPEN_REVOKE_UPDATE_URL",
    )

    # Security: Fernet key that encrypts connector secrets. Required, the app
    # refuses to start without it. Generate one with the command in .env.example.
    open_revoke_secret_key: SecretStr

    # Sync
    sync_interval_hours: int = Field(default=6, ge=1)

    # App discovery scan (Google sign-ins to third-party apps). The first scan reads
    # ``scan_lookback_days`` of the audit log (Google keeps at most 180); later scans read
    # from the end of the last one minus ``scan_overlap_hours``, because Google adds
    # audit events with a delay.
    scan_interval_hours: int = Field(default=24, ge=1)
    scan_lookback_days: int = Field(default=180, ge=1, le=180)
    scan_overlap_hours: int = Field(default=72, ge=0, le=24 * 30)

    # Write actions (ExecuteActionWorkflow): after the write, the account list is
    # read again up to ``action_verify_attempts`` times, ``action_verify_delay_seconds``
    # apart. Tests and development may use 1 s. An action waits for the connection
    # lock (a sync or another action) at most ``action_lock_wait_seconds``.
    action_verify_attempts: int = Field(default=3, ge=1, le=10)
    action_verify_delay_seconds: int = Field(default=30, ge=0, le=600)
    action_lock_wait_seconds: int = Field(default=600, ge=1, le=3600)

    # Development: show the "fake" connector (deterministic test data) in the
    # catalog. Also on when DEBUG is true. Never enable it for real data.
    enable_fake_connector: bool = Field(default=False, validation_alias="OPEN_REVOKE_ENABLE_FAKE_CONNECTOR")

    # Development: GET /api/auth/state returns ``dev_prefill``, values the sign-in forms
    # (setup, login, registration, password reset) fill with one click. Anyone who opens
    # the panel sees this password, so never enable it for a panel with real data.
    dev_prefill: bool = Field(default=False, validation_alias="OPEN_REVOKE_DEV_PREFILL")
    dev_prefill_organization: str = "Acme Dev"
    dev_prefill_currency: str = "EUR"
    dev_prefill_name: str = "Dev Admin"
    dev_prefill_email: str = "admin@example.com"
    dev_prefill_password: str = "open-revoke-dev-password"
    dev_prefill_invitee_name: str = "Dev User"
    dev_prefill_signup_email: str = "new.user@example.com"

    # Panel sign-in (skills/backend/auth.md). Address of the panel as users open it: invite and
    # password reset links point here. Never taken from the request's Host header.
    public_url: str = "http://localhost:18410"
    session_ttl_hours: int = Field(default=168, ge=1, le=24 * 90)
    # Secure flag of the session cookie. None: on when public_url is https.
    session_cookie_secure: bool | None = None
    # "Connect with Google" (Google Workspace through OAuth). Google sends the admin back to
    # <base>/api/discovery/google-oauth/callback; the base defaults to public_url. Google accepts plain
    # http only for localhost and needs a public TLD otherwise, so a dev host like *.localhost
    # sets a localhost base here.
    google_oauth_redirect_base: str | None = None
    # Google Cloud project the automatic setup uses (instead of creating one) when it has no
    # earlier run to reuse. Development: the project made for this installation.
    google_cloud_project_id: str | None = None

    # Development: a Google Workspace connection the seeder creates on every `db reset`, so a
    # reset does not mean connecting Google again. All four values or none; they come from
    # `.env` (git-ignored). Never set them in a shared or production deployment.
    seed_google_admin_email: str | None = None
    seed_google_oauth_client_id: str | None = None
    seed_google_oauth_client_secret: SecretStr | None = None
    seed_google_oauth_refresh_token: SecretStr | None = None
    invite_ttl_hours: int = Field(default=168, ge=1, le=24 * 30)

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/open_revoke"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Temporal
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "open-revoke"

    # Shared browser (service `browser` in compose.yaml, skills/backend/browser.md).
    # The backend connects to CDP by the container's IP: Chrome rejects HTTP
    # requests whose Host header is a name other than localhost.
    browser_cdp_host: str = "browser"
    browser_cdp_port: int = 9223
    # Live view: the API proxies the noVNC page and its WebSocket from the browser container
    # (app/browser/live_proxy.py), behind the panel session, so no browser port is published.
    # live.html (docker/browser/live.html): the screen scaled to the live view, no noVNC menu.
    browser_live_port: int = 6080
    browser_live_view_url: str | None = "/api/browser/live/live.html?quality=9&compression=0"

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

    # Browser origins allowed to call the API across origins. The panel proxies /api on its own
    # origin, so this is rarely needed; the origin of PUBLIC_URL is always added (trusted_origins).
    cors_origins: list[str] = ["http://localhost:18410", "http://127.0.0.1:18410"]

    # Host names the API answers to (Host and X-Forwarded-Host, without the port). Anything else
    # gets 400: protection against DNS rebinding. "app" and "open-revoke-app" are the names inside
    # the compose network. The hosts of PUBLIC_URL and GOOGLE_OAUTH_REDIRECT_BASE are always added
    # (trusted_hosts), so a custom domain needs only PUBLIC_URL. "*" turns the check off.
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "[::1]", "app", "open-revoke-app"]

    @property
    def trusted_hosts(self) -> list[str]:
        extra = [urlsplit(url).hostname for url in (self.public_url, self.google_oauth_redirect_base) if url]
        return list(dict.fromkeys([*self.allowed_hosts, *(host for host in extra if host)]))

    @property
    def public_origin(self) -> str:
        parts = urlsplit(self.public_url)
        return f"{parts.scheme}://{parts.netloc}"

    @property
    def trusted_origins(self) -> list[str]:
        return list(dict.fromkeys([*self.cors_origins, self.public_origin]))

    @property
    def cookie_secure(self) -> bool:
        if self.session_cookie_secure is not None:
            return self.session_cookie_secure
        return self.public_url.startswith("https://")

    @property
    def google_oauth_redirect_uri(self) -> str:
        base = (self.google_oauth_redirect_base or self.public_url).rstrip("/")
        return f"{base}/api/discovery/google-oauth/callback"

    @field_validator("public_url")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator("open_revoke_secret_key")
    @classmethod
    def _must_be_fernet_key(cls, value: SecretStr) -> SecretStr:
        try:
            Fernet(value.get_secret_value().encode())
        except ValueError as exc:
            raise ValueError(
                "OPEN_REVOKE_SECRET_KEY must be a Fernet key (32 url-safe base64-encoded bytes). "
                "Generate one with the command in .env.example."
            ) from exc
        return value


settings = Settings()
