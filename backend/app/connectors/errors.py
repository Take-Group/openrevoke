"""Errors a connector raises. Own module, so ``browser_api`` and ``recipes`` need not import ``base``."""


class ConnectorError(Exception):
    """The app returned an error or data the connector cannot use."""


class NeedsLogin(ConnectorError):  # noqa: N818 - public name in the connector interface
    """No browser session, or the app rejected the credentials (401).

    Sync stops with status ``needs_login`` and leaves accounts as they are.
    """


class IncompleteListError(ConnectorError):
    """The connector could not read the full list (pagination broke off)."""
