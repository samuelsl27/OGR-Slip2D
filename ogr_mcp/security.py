# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Who may talk to the HTTP server.

``python_exec`` is always available (the owner's decision), so whoever
reaches this endpoint can run code on the machine. Three consequences, all
enforced here and in ``cli.py``:

* **A bearer token, always** — also on 127.0.0.1. "Only local" is not a
  boundary on its own: any web page the user visits can make the browser
  send requests to localhost, and a DNS-rebinding page can even make them
  look same-origin. The token is compared in constant time.
* **Host and Origin are checked** (the SDK's DNS-rebinding protection,
  switched ON — its default is off for backwards compatibility): a Host
  that is not this server's is refused with 421, a foreign Origin with 403.
* **No token, no network.** A host that is not loopback needs an explicit
  token (``--token``, ``--token-file`` or ``OGR_MCP_TOKEN``); ``--no-auth``
  is accepted only on loopback. ``cli.py`` refuses to start otherwise.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import hmac
import ipaddress
import secrets

LOOPBACK_NAMES = ("localhost",)


def is_loopback(host: str) -> bool:
    if host in LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return False


def new_token() -> str:
    return secrets.token_urlsafe(32)


class BearerAuth:
    """ASGI middleware: every HTTP request needs ``Authorization: Bearer``."""

    def __init__(self, app, token: str) -> None:
        self.app = app
        self._expected = f"Bearer {token}".encode("latin-1")

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            got = b""
            for key, value in scope.get("headers", ()):
                if key.lower() == b"authorization":
                    got = value
                    break
            if not hmac.compare_digest(got, self._expected):
                body = (b'{"error": "missing or invalid bearer token"}')
                await send({"type": "http.response.start", "status": 401,
                            "headers": [
                                (b"content-type", b"application/json"),
                                (b"www-authenticate",
                                 b'Bearer realm="ogr-slip2d"')]})
                await send({"type": "http.response.body", "body": body})
                return
        await self.app(scope, receive, send)


def transport_security(host: str, port: int, extra_origins=()):
    """The SDK's Host/Origin protection, configured for this server."""
    from mcp.server.transport_security import TransportSecuritySettings

    hosts = {f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}",
             f"{host}:{port}"}
    origins = {f"http://127.0.0.1:{port}", f"http://localhost:{port}",
               *extra_origins}
    return TransportSecuritySettings(enable_dns_rebinding_protection=True,
                                     allowed_hosts=sorted(hosts),
                                     allowed_origins=sorted(origins))


def http_app(server, *, host: str, port: int, token, extra_origins=()):
    """The streamable-HTTP ASGI app, stateless, behind the token."""
    app = server.streamable_http_app(
        json_response=True, stateless_http=True, host=host,
        transport_security=transport_security(host, port, extra_origins))
    return BearerAuth(app, token) if token else app
