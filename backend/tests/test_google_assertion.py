"""The Google service account assertion is a valid RS256 JWT (signed without google-auth)."""

import base64
import json

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa

from app.connectors.google_workspace.auth import DEFAULT_TOKEN_URI, build_assertion


def _pem(key: rsa.RSAPrivateKey | ec.EllipticCurvePrivateKey) -> str:
    return key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()


def _part(segment: str) -> dict:
    return json.loads(base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4)))


def test_assertion_is_signed_with_the_service_account_key() -> None:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    info = {"client_email": "sa@p.iam.gserviceaccount.com", "private_key": _pem(key), "private_key_id": "k1"}
    token = build_assertion(info, "admin@example.com", ["scope-a", "scope-b"], now=1_800_000_000)
    header, payload, signature = token.split(".")
    assert _part(header) == {"typ": "JWT", "alg": "RS256", "kid": "k1"}
    assert _part(payload) == {
        "iss": "sa@p.iam.gserviceaccount.com",
        "sub": "admin@example.com",
        "scope": "scope-a scope-b",
        "aud": DEFAULT_TOKEN_URI,
        "iat": 1_800_000_000,
        "exp": 1_800_003_600,
    }
    raw = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
    key.public_key().verify(raw, f"{header}.{payload}".encode(), padding.PKCS1v15(), hashes.SHA256())


@pytest.mark.parametrize("private_key", ["not a key", _pem(ec.generate_private_key(ec.SECP256R1()))])
def test_a_key_that_is_not_rsa_is_refused(private_key: str) -> None:
    with pytest.raises(ValueError):
        build_assertion({"client_email": "sa@p", "private_key": private_key}, "admin@example.com", ["s"])
