# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
OAuth 2.1 for remote clients (spec 008, F4b): the server is its own
authorization server, and the owner approves with the server's token.

WHY. ChatGPT connects only to public HTTPS servers and only through OAuth
2.1 — PKCE with S256, the protected-resource and authorization-server
metadata, dynamic client registration, and tokens bound to the resource.
It does not take a static bearer header (OpenAI's Apps SDK documentation,
read on 2026-09-24). This server's rule is that nobody talks to it without
the server's token (AGENTS.md: ``python_exec`` is always available), so
OAuth here is a way of HANDING OVER access with that token, not of
replacing it:

* ``/authorize`` sends the browser to ``/approve``, a page of this server
  that shows which client asks and requires the server's token. Knowing
  the token is being the owner. Failures are slowed down; after a few the
  request is locked, and after more across ALL requests every approval is
  refused for a while (anyone can open a new request, so a per-request
  limit alone would not bound the guessing).
* An approval yields an authorization code (PKCE S256, one use, 5 min),
  then an opaque access token bound to the resource (the audience ChatGPT
  echoes), valid for an hour, with a refresh token. Everything lives in
  memory: a restart revokes every token.
* The static token keeps working as ``Authorization: Bearer`` for clients
  that can send headers (the OpenAI API and Agents SDK, Claude Code).
* Registration is dynamic (RFC 7591), and redirect URIs must be on an
  allowlist: ChatGPT's and Claude's callbacks, loopback addresses (a local
  client's own callback), and any added with ``--oauth-redirect``. Client
  ID metadata documents (CIMD) are not offered: they would make the server
  fetch a document from the client's host, a network call nobody asked of
  it.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import hmac
import html
import ipaddress
import re
import secrets
import threading
import time
from typing import Optional
from urllib.parse import urlencode, urlparse

#: Callbacks accepted without being named: ChatGPT's two (with and
#: without issuer identification) and Claude's.
DEFAULT_REDIRECTS = (
    "https://chatgpt.com/connector_platform_oauth_redirect",
    "https://chatgpt.com/connector/oauth/",          # + {callback_id}
    "https://claude.ai/api/mcp/auth_callback",
)
ACCESS_TTL_S = 3600
REFRESH_TTL_S = 30 * 24 * 3600
CODE_TTL_S = 300
PENDING_TTL_S = 600
MAX_FAILURES = 5
#: Wrong tokens across every request before approvals stop for a while.
MAX_GLOBAL_FAILURES = 20
GLOBAL_WINDOW_S = 600
STATIC_CLIENT = "static-token"
#: What may follow a prefix entry of the redirect allowlist.
_SEGMENT = re.compile(r"[A-Za-z0-9_-]+")


def _loopback_redirect(uri: str) -> bool:
    try:
        u = urlparse(uri)
        host = (u.hostname or "")
        if u.scheme != "http":
            return False
        return host == "localhost" or ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def redirect_allowed(uri: str, extra=()) -> bool:
    """Whether a client may be sent back to ``uri``.

    An entry ending in ``/`` is a prefix for ONE more path segment of
    identifier characters (ChatGPT's ``…/connector/oauth/{callback_id}``);
    the bare prefix, a longer path, a query or a fragment do not match.
    Any other entry matches exactly.
    """
    uri = str(uri)
    for allowed in tuple(DEFAULT_REDIRECTS) + tuple(extra):
        if allowed.endswith("/"):
            if uri.startswith(allowed) and \
                    _SEGMENT.fullmatch(uri[len(allowed):]):
                return True
        elif uri == allowed:
            return True
    return _loopback_redirect(uri)


class OwnerApprovalProvider:
    """``OAuthAuthorizationServerProvider`` for a single owner.

    ``token`` is the server's token; ``resource`` the MCP endpoint's public
    URL (the audience every issued token is bound to); ``approve_url`` the
    public URL of the approval page.
    """

    def __init__(self, token: str, resource: str, approve_url: str,
                 extra_redirects=()) -> None:
        self._token = token.encode("utf-8")
        self.resource = str(resource)
        self.approve_url = str(approve_url)
        self.extra_redirects = tuple(extra_redirects)
        self._lock = threading.Lock()
        self.clients: dict = {}
        self.pending: dict = {}         # request id -> dict
        self.codes: dict = {}
        self.access: dict = {}
        self.refresh: dict = {}
        self._failures: list = []       # times of wrong tokens, any request

    # -- the owner ------------------------------------------------------
    def owner_token_ok(self, candidate: str) -> bool:
        return hmac.compare_digest(str(candidate).encode("utf-8"),
                                   self._token)

    # -- registration ---------------------------------------------------
    async def get_client(self, client_id: str):
        return self.clients.get(client_id)

    async def register_client(self, client_info) -> None:
        from mcp.server.auth.provider import RegistrationError

        bad = [str(u) for u in (client_info.redirect_uris or [])
               if not redirect_allowed(str(u), self.extra_redirects)]
        if bad or not client_info.redirect_uris:
            raise RegistrationError(
                "invalid_redirect_uri",
                f"Redirect URI not allowed by this server: {bad or 'none'}. "
                f"Start it with --oauth-redirect to add one.")
        with self._lock:
            self.clients[client_info.client_id] = client_info

    # -- authorization --------------------------------------------------
    async def authorize(self, client, params) -> str:
        from mcp.server.auth.provider import AuthorizeError

        if params.resource is not None and \
                str(params.resource).rstrip("/") != self.resource.rstrip("/"):
            raise AuthorizeError("invalid_target",
                                 "This server is a different resource.")
        rid = secrets.token_urlsafe(16)
        with self._lock:
            self._expire()
            self.pending[rid] = {"client": client, "params": params,
                                 "created": time.time(), "failures": 0}
        return f"{self.approve_url}?{urlencode({'request': rid})}"

    def pending_request(self, rid: str) -> Optional[dict]:
        with self._lock:
            self._expire()
            return self.pending.get(rid)

    def approve(self, rid: str, candidate: str) -> tuple:
        """``(redirect_url, None)`` on success, ``(None, message)`` if not."""
        from mcp.server.auth.provider import (AuthorizationCode,
                                              construct_redirect_uri)

        with self._lock:
            self._expire()
            req = self.pending.get(rid)
            if req is None:
                return None, "This request has expired; start again."
            now = time.time()
            self._failures = [t for t in self._failures
                              if now - t < GLOBAL_WINDOW_S]
            if len(self._failures) >= MAX_GLOBAL_FAILURES:
                return None, ("Too many wrong tokens on this server: "
                              "approvals are stopped for a few minutes.")
            if req["failures"] >= MAX_FAILURES:
                return None, "Too many wrong tokens: this request is locked."
            if not self.owner_token_ok(candidate):
                req["failures"] += 1
                self._failures.append(now)
                return None, "That is not this server's token."
            del self.pending[rid]
        params, client = req["params"], req["client"]
        code = secrets.token_urlsafe(32)
        self.codes[code] = AuthorizationCode(
            code=code, scopes=list(params.scopes or []),
            expires_at=time.time() + CODE_TTL_S,
            client_id=client.client_id,
            code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=(
                params.redirect_uri_provided_explicitly),
            resource=self.resource, subject="owner")
        return construct_redirect_uri(str(params.redirect_uri), code=code,
                                      state=params.state), None

    def _expire(self) -> None:
        now = time.time()
        for rid in [r for r, q in self.pending.items()
                    if now - q["created"] > PENDING_TTL_S]:
            del self.pending[rid]

    # -- tokens ---------------------------------------------------------
    async def load_authorization_code(self, client, authorization_code):
        code = self.codes.get(authorization_code)
        if code is None or code.client_id != client.client_id or \
                code.expires_at < time.time():
            return None
        return code

    def _issue(self, client_id: str, scopes: list):
        from mcp.server.auth.provider import AccessToken, RefreshToken
        from mcp.shared.auth import OAuthToken

        now = int(time.time())
        at = secrets.token_urlsafe(32)
        rt = secrets.token_urlsafe(32)
        self.access[at] = AccessToken(
            token=at, client_id=client_id, scopes=list(scopes),
            expires_at=now + ACCESS_TTL_S, resource=self.resource,
            subject="owner")
        self.refresh[rt] = RefreshToken(
            token=rt, client_id=client_id, scopes=list(scopes),
            expires_at=now + REFRESH_TTL_S, resource=self.resource,
            subject="owner")
        return OAuthToken(access_token=at, token_type="Bearer",
                          expires_in=ACCESS_TTL_S, refresh_token=rt,
                          scope=" ".join(scopes) or None)

    async def exchange_authorization_code(self, client, authorization_code):
        self.codes.pop(authorization_code.code, None)     # one use
        return self._issue(client.client_id, authorization_code.scopes)

    async def load_refresh_token(self, client, refresh_token):
        rt = self.refresh.get(refresh_token)
        if rt is None or rt.client_id != client.client_id or \
                (rt.expires_at and rt.expires_at < time.time()):
            return None
        return rt

    async def exchange_refresh_token(self, client, refresh_token, scopes):
        self.refresh.pop(refresh_token.token, None)       # rotated
        return self._issue(client.client_id,
                           scopes or refresh_token.scopes)

    async def load_access_token(self, token: str):
        from mcp.server.auth.provider import AccessToken

        if self.owner_token_ok(token):
            # The server's own token, for clients that send headers.
            return AccessToken(token=token, client_id=STATIC_CLIENT,
                               scopes=[], resource=self.resource,
                               subject="owner")
        at = self.access.get(token)
        if at is None or (at.expires_at and at.expires_at < time.time()):
            return None
        return at

    async def revoke_token(self, token) -> None:
        self.access.pop(getattr(token, "token", ""), None)
        self.refresh.pop(getattr(token, "token", ""), None)

    async def exchange_identity_assertion(self, client, params):
        from mcp.server.auth.provider import TokenError
        raise TokenError("unsupported_grant_type",
                         "Identity assertions are not accepted.")


# ----------------------------------------------------------------------
# The approval page
# ----------------------------------------------------------------------
def approval_page(provider: OwnerApprovalProvider, rid: str,
                  error: Optional[str] = None) -> str:
    req = provider.pending_request(rid)
    if req is None:
        body = "<p>This request has expired or does not exist.</p>"
    else:
        client = req["client"]
        name = html.escape(str(getattr(client, "client_name", None)
                               or client.client_id))
        back = html.escape(urlparse(str(req["params"].redirect_uri))
                           .netloc)
        err = (f"<p style='color:#b00'>{html.escape(error)}</p>"
               if error else "")
        body = f"""
<p><b>{name}</b> asks to use this OGR Slip2D server, and will be sent
back to <b>{back}</b>.</p>
<p>Approving lets it run every tool, including <code>python_exec</code>,
which runs code on this machine as you.</p>
{err}
<form method="post">
<input type="hidden" name="request" value="{html.escape(rid)}">
<label>Server token: <input type="password" name="token"
autocomplete="off" autofocus></label>
<button type="submit">Approve</button>
</form>"""
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>OGR Slip2D — approve access</title></head>
<body style="font-family:sans-serif;max-width:36em;margin:3em auto">
<h1>OGR Slip2D</h1>{body}</body></html>"""


def install_approval_route(server, provider: OwnerApprovalProvider,
                           path: str = "/approve") -> None:
    """Add ``/approve`` to ``server`` (an ``MCPServer``)."""
    import anyio
    from starlette.responses import HTMLResponse, RedirectResponse

    # The owner types the server's token on this page: no other site may
    # frame it (a transparent frame over a decoy would collect the token),
    # and neither the page nor where it came from may be kept.
    headers = {"X-Frame-Options": "DENY",
               "Content-Security-Policy": "frame-ancestors 'none'",
               "Cache-Control": "no-store",
               "Referrer-Policy": "no-referrer"}

    @server.custom_route(path, methods=["GET", "POST"])
    async def approve(request):
        if request.method == "GET":
            rid = request.query_params.get("request", "")
            return HTMLResponse(approval_page(provider, rid),
                                headers=headers)
        form = await request.form()
        rid = str(form.get("request", ""))
        target, error = provider.approve(rid, str(form.get("token", "")))
        if target is None:
            await anyio.sleep(1.0)          # slow a guessing loop down
            return HTMLResponse(approval_page(provider, rid, error),
                                status_code=401, headers=headers)
        return RedirectResponse(target, status_code=302, headers=headers)
