"""Input rules with a security reason: e-mail shape, link schemes, which config fields hold a secret's address."""

import pytest
from pydantic import ValidationError

from app.connectors.github.connector import GitHubConnector
from app.connectors.scim.connector import ScimConnector
from app.schemas.apps import AppCreate, AppUpdate
from app.schemas.auth import SignupRequest


def test_email_with_two_at_signs_is_refused() -> None:
    # The domain check of self sign-up takes the last part: "a@evil.com@example.com" must not pass.
    with pytest.raises(ValidationError):
        SignupRequest(name="A", email="a@evil.com@example.com", password="correct horse battery")


@pytest.mark.parametrize("url", ["javascript:alert(1)", "data:text/html,x", "//evil.example", "ftp://x.example"])
def test_app_links_must_be_http(url: str) -> None:
    with pytest.raises(ValidationError):
        AppCreate(name="X", website=url)
    with pytest.raises(ValidationError):
        AppUpdate(admin_url=url)


def test_app_links_accept_http_and_empty() -> None:
    assert AppCreate(name="X", website="https://x.example", admin_url="http://x.example/admin").website
    assert AppUpdate(website="").website == ""


def test_url_fields_bind_the_secrets() -> None:
    assert ScimConnector.endpoint_of({"base_url": "https://a.example/scim/v2", "user_filter": "x"}) == {
        "base_url": "https://a.example/scim/v2"
    }
    assert GitHubConnector.endpoint_of({"org": "a", "api_url": "https://api.github.com"}) == {
        "api_url": "https://api.github.com"
    }
