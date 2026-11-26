"""Address of the client, for sign-in rate limits and the audit log.

The API sits behind the panel (Next.js), which passes ``X-Forwarded-For`` on and sets it to its own
peer when the request had none. Behind a reverse proxy (the bundled Caddy, nginx, Cloudflare) the
last entry is the address the proxy saw. Without a proxy in front, a client can write any value
into the header; the panel port is meant to be bound to 127.0.0.1 behind a proxy (SECURITY.md).
"""

from fastapi import Request


def client_ip(request: Request) -> str:
    forwarded = [part.strip() for part in request.headers.get("x-forwarded-for", "").split(",") if part.strip()]
    if forwarded:
        return forwarded[-1][:64]
    return request.client.host if request.client else "unknown"
