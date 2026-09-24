# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.204 (spec 008, F4b) — the server on the Internet: OAuth 2.1 on top of
the token, and HTTPS.

ChatGPT connects only to public HTTPS servers and only through OAuth 2.1:
PKCE with S256, the protected-resource and authorization-server metadata,
dynamic client registration, and tokens bound to the resource. This
server's rule is that nobody talks to it without the server's token,
because ``python_exec`` is always there. So OAuth here HANDS OVER access
with that token; it does not replace it.

Invariants protected:

* **The whole flow works against a real process.** It goes register →
  authorize → approval page → the owner types the server's token → code →
  token with PKCE → an authenticated MCP call. It also covers refresh
  (rotating) and revocation.
* **Nothing without the token.** ``/mcp`` answers 401 without a bearer.
  The approval page refuses a wrong token (401) and locks the request after
  a few; past a global limit it stops every approval, because anyone can
  open a new request. A code is single-use, and needs its PKCE verifier.
  With ``--public-url`` a token shorter than 32 characters is refused.
* **The static token still works** as a bearer for clients that send
  headers (Claude Code, the OpenAI Agents SDK).
* **Audience.** A token issued for another resource is refused, and so is
  an authorization request for another resource.
* **Redirect allowlist.** ChatGPT's and Claude's callbacks and loopback
  addresses register; anything else does not, unless named with
  ``--oauth-redirect``.
* **Behind a tunnel** the public ``Host`` is accepted, and any other is
  still refused (421).
* **The command line keeps the rules.**
  - ``--public-url`` never goes with ``--no-auth``.
  - ``--public-url`` must be https (http only on loopback, to test).
  - The TLS pair goes together.
  - The HTTP options are refused over stdio.
* **HTTPS directly** with ``--tls-cert``/``--tls-key``. The test uses a
  self-signed certificate made on the spot; it is skipped without
  ``cryptography``.

Every test that needs the SDK returns early without it, except in CI.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import os
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

_ROOT = Path(__file__).resolve().parent.parent
_TOKEN = "owner-token-" + "x" * 20
_CHATGPT = "https://chatgpt.com/connector/oauth/cb-test-123"


def _have_mcp() -> bool:
    try:
        import mcp  # noqa: F401
    except ImportError:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            raise AssertionError("the mcp SDK must be installed in CI")
        return False
    return True


def _env(**extra) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("OGR_MCP_TOKEN", None)
    env.update(extra)
    return env


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _start(port: int, *args, scheme="http", verify=True):
    """The server as a process; returns it once its metadata answers."""
    import httpx2
    proc = subprocess.Popen(
        [sys.executable, "-m", "ogr_mcp", "--transport", "http",
         "--port", str(port), *args],
        cwd=str(_ROOT), env=_env(OGR_MCP_TOKEN=_TOKEN),
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    probe = (f"{scheme}://127.0.0.1:{port}"
             "/.well-known/oauth-authorization-server")
    deadline = time.time() + 40
    while time.time() < deadline:
        if proc.poll() is not None:
            raise AssertionError(proc.stderr.read().decode("utf-8",
                                                           "replace"))
        try:
            httpx2.get(probe, timeout=0.5, verify=verify)
            break
        except Exception:  # noqa: BLE001 - not up yet
            time.sleep(0.2)
    return proc


def _stop(proc) -> None:
    proc.terminate()
    try:
        proc.wait(15)
    except subprocess.TimeoutExpired:  # pragma: no cover
        proc.kill()


def _pkce():
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).decode("ascii").rstrip("=")
    return verifier, challenge


async def _mcp_call(url: str, bearer: str, verify=True):
    import httpx2
    from mcp import Client
    from mcp.client.streamable_http import streamable_http_client
    hc = httpx2.AsyncClient(headers={"authorization": f"Bearer {bearer}"},
                            verify=verify)
    async with Client(streamable_http_client(url, http_client=hc)) as c:
        return await c.call_tool("project_new", {"name": "remote"})


class TestTheOAuthFlow:
    """One server for the whole flow: each step needs the previous one."""

    def test_register_approve_token_call_refresh_revoke(self):
        if not _have_mcp():
            return
        import httpx2
        port = _free_port()
        base = f"http://127.0.0.1:{port}"
        mcp_url = f"{base}/mcp"
        proc = _start(port, "--public-url", base)
        try:
            # -- the metadata is public and points where it must --------
            prm = httpx2.get(f"{base}/.well-known/oauth-protected-resource"
                             "/mcp").json()
            assert prm["resource"].rstrip("/") == mcp_url, prm
            assert any(a.rstrip("/") == base
                       for a in prm["authorization_servers"]), prm
            asm = httpx2.get(f"{base}/.well-known/oauth-authorization-server"
                             ).json()
            assert asm["code_challenge_methods_supported"] == ["S256"]
            assert asm["registration_endpoint"].endswith("/register")

            # -- /mcp without a bearer: 401, pointing at the metadata ----
            body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list",
                    "params": {}}
            h = {"content-type": "application/json",
                 "accept": "application/json, text/event-stream"}
            r = httpx2.post(mcp_url, json=body, headers=h)
            assert r.status_code == 401
            assert "oauth-protected-resource" in \
                r.headers.get("www-authenticate", "")

            # -- registration: the allowlist -----------------------------
            bad = httpx2.post(f"{base}/register", json={
                "redirect_uris": ["https://evil.example/cb"],
                "token_endpoint_auth_method": "none",
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"]})
            assert bad.status_code == 400, bad.text
            assert "redirect" in bad.text
            reg = httpx2.post(f"{base}/register", json={
                "redirect_uris": [_CHATGPT], "client_name": "ChatGPT test",
                "token_endpoint_auth_method": "none",
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"]})
            assert reg.status_code == 201, reg.text
            client_id = reg.json()["client_id"]

            # -- authorize: sent to the owner's page ---------------------
            verifier, challenge = _pkce()
            q = {"response_type": "code", "client_id": client_id,
                 "redirect_uri": _CHATGPT, "code_challenge": challenge,
                 "code_challenge_method": "S256", "state": "st-1",
                 "resource": mcp_url}
            r = httpx2.get(f"{base}/authorize", params=q)
            assert r.status_code in (302, 307), r.text
            page = r.headers["location"]
            assert page.startswith(f"{base}/approve?request="), page
            rid = parse_qs(urlparse(page).query)["request"][0]
            shown = httpx2.get(page)
            html = shown.text
            assert "ChatGPT test" in html and "python_exec" in html
            # The token is typed here: nobody may frame or keep the page.
            assert shown.headers["x-frame-options"] == "DENY"
            assert "frame-ancestors 'none'" in \
                shown.headers["content-security-policy"]
            assert shown.headers["cache-control"] == "no-store"
            assert "chatgpt.com" in html

            # -- a wrong token is refused, slowly ------------------------
            t0 = time.monotonic()
            r = httpx2.post(f"{base}/approve",
                            data={"request": rid, "token": "guess"})
            assert r.status_code == 401
            assert time.monotonic() - t0 >= 0.9

            # -- the owner approves --------------------------------------
            r = httpx2.post(f"{base}/approve",
                            data={"request": rid, "token": _TOKEN})
            assert r.status_code == 302, r.text
            back = urlparse(r.headers["location"])
            assert f"{back.scheme}://{back.netloc}{back.path}" == _CHATGPT
            got = parse_qs(back.query)
            assert got["state"] == ["st-1"]
            code = got["code"][0]
            # The request is spent: approving it again does nothing.
            again = httpx2.post(f"{base}/approve",
                                data={"request": rid, "token": _TOKEN})
            assert again.status_code == 401

            # -- the code needs its verifier, and serves once ------------
            form = {"grant_type": "authorization_code", "code": code,
                    "redirect_uri": _CHATGPT, "client_id": client_id,
                    "resource": mcp_url}
            wrong = httpx2.post(f"{base}/token", data={
                **form, "code_verifier": _pkce()[0]})
            assert wrong.status_code == 400, wrong.text
            tok = httpx2.post(f"{base}/token", data={
                **form, "code_verifier": verifier})
            assert tok.status_code == 200, tok.text
            tokens = tok.json()
            assert tokens["token_type"].lower() == "bearer"
            reuse = httpx2.post(f"{base}/token", data={
                **form, "code_verifier": verifier})
            assert reuse.status_code == 400

            # -- an MCP call with the issued token, and with the static --
            r = asyncio.run(_mcp_call(mcp_url, tokens["access_token"]))
            assert not r.is_error and r.structured_content["name"] == \
                "remote"
            r = asyncio.run(_mcp_call(mcp_url, _TOKEN))
            assert not r.is_error

            # -- refresh rotates -----------------------------------------
            ref = {"grant_type": "refresh_token", "client_id": client_id,
                   "refresh_token": tokens["refresh_token"]}
            new = httpx2.post(f"{base}/token", data=ref)
            assert new.status_code == 200, new.text
            assert httpx2.post(f"{base}/token", data=ref).status_code == 400
            fresh = new.json()["access_token"]

            # -- revocation ends a token ---------------------------------
            # The SDK (mcp 2.2) declares client_secret required in its
            # RevocationRequest even for a public client, whose
            # authentication then ignores it; RFC 7009 would let it be
            # left out. Reported in the changelog, not patched here.
            rv = httpx2.post(f"{base}/revoke", data={
                "token": fresh, "client_id": client_id, "client_secret": ""})
            assert rv.status_code == 200, rv.text
            r = httpx2.post(mcp_url, json=body, headers={
                **h, "authorization": f"Bearer {fresh}"})
            assert r.status_code == 401

            # -- another resource is refused at authorization ------------
            other = httpx2.get(f"{base}/authorize", params={
                **q, "resource": "https://other.example/mcp"})
            loc = other.headers.get("location", "")
            assert "invalid_target" in loc or other.status_code == 400, \
                (other.status_code, loc)
        finally:
            _stop(proc)

    def test_the_public_host_is_accepted_and_no_other(self):
        if not _have_mcp():
            return
        import httpx2
        port = _free_port()
        proc = _start(port, "--public-url", "https://ogr.example.test")
        try:
            url = f"http://127.0.0.1:{port}/mcp"
            body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list",
                    "params": {}}
            h = {"content-type": "application/json",
                 "accept": "application/json, text/event-stream",
                 "authorization": f"Bearer {_TOKEN}"}
            ok = httpx2.post(url, json=body, headers={
                **h, "host": "ogr.example.test",
                "origin": "https://ogr.example.test"})
            assert ok.status_code == 200, ok.text
            assert httpx2.post(url, json=body, headers={
                **h, "host": "evil.example"}).status_code == 421
            meta = httpx2.get(f"http://127.0.0.1:{port}/.well-known/"
                              "oauth-authorization-server").json()
            assert meta["issuer"].rstrip("/") == "https://ogr.example.test"
        finally:
            _stop(proc)


class TestTheProvider:
    """The rules that need no server."""

    def _provider(self, **kw):
        from ogr_mcp.oauth import OwnerApprovalProvider
        return OwnerApprovalProvider(
            _TOKEN, resource="https://ogr.example.test/mcp",
            approve_url="https://ogr.example.test/approve", **kw)

    def _pending(self, p):
        from mcp.server.auth.provider import AuthorizationParams
        from mcp.shared.auth import OAuthClientInformationFull
        client = OAuthClientInformationFull(
            client_id="c1", redirect_uris=[_CHATGPT],
            token_endpoint_auth_method="none")
        params = AuthorizationParams(
            state="s", scopes=[], code_challenge="x" * 43,
            redirect_uri=_CHATGPT, redirect_uri_provided_explicitly=True,
            resource="https://ogr.example.test/mcp")
        url = asyncio.run(p.authorize(client, params))
        return parse_qs(urlparse(url).query)["request"][0]

    def test_a_request_locks_after_a_few_wrong_tokens(self):
        if not _have_mcp():
            return
        from ogr_mcp.oauth import MAX_FAILURES
        p = self._provider()
        rid = self._pending(p)
        for _ in range(MAX_FAILURES):
            target, msg = p.approve(rid, "guess")
            assert target is None and "not" in msg
        target, msg = p.approve(rid, _TOKEN)
        assert target is None and "locked" in msg

    def test_new_requests_do_not_reset_the_guessing(self):
        """Anyone can open a request; a per-request limit alone would let
        a guesser open another. Past the global limit every approval stops,
        the owner's too, until the window passes."""
        if not _have_mcp():
            return
        from ogr_mcp.oauth import MAX_FAILURES, MAX_GLOBAL_FAILURES
        p = self._provider()
        tried = 0
        while tried < MAX_GLOBAL_FAILURES:
            rid = self._pending(p)
            for _ in range(min(MAX_FAILURES, MAX_GLOBAL_FAILURES - tried)):
                p.approve(rid, "guess")
                tried += 1
        target, msg = p.approve(self._pending(p), _TOKEN)
        assert target is None and "stopped" in msg
        p._failures = []                    # the window passes
        target, msg = p.approve(self._pending(p), _TOKEN)
        assert target is not None, msg

    def test_a_token_for_another_resource_is_refused(self):
        if not _have_mcp():
            return
        from mcp.server.auth.middleware.bearer_auth import BearerAuthBackend
        from mcp.server.auth.provider import AccessToken, ProviderTokenVerifier
        from pydantic import AnyHttpUrl
        from starlette.requests import HTTPConnection
        p = self._provider()
        p.access["mine"] = AccessToken(
            token="mine", client_id="c1", scopes=[],
            resource="https://ogr.example.test/mcp")
        p.access["theirs"] = AccessToken(
            token="theirs", client_id="c1", scopes=[],
            resource="https://other.example/mcp")
        backend = BearerAuthBackend(
            ProviderTokenVerifier(p),
            resource_server_url=AnyHttpUrl("https://ogr.example.test/mcp"))

        def auth(tok):
            conn = HTTPConnection({"type": "http", "headers": [
                (b"authorization", f"Bearer {tok}".encode())]})
            return asyncio.run(backend.authenticate(conn))
        assert auth("mine") is not None
        assert auth("theirs") is None
        assert auth(_TOKEN) is not None       # the static token
        assert auth("nothing") is None

    def test_the_redirect_allowlist(self):
        from ogr_mcp.oauth import redirect_allowed
        assert redirect_allowed(
            "https://chatgpt.com/connector_platform_oauth_redirect")
        assert redirect_allowed(_CHATGPT)
        assert redirect_allowed("https://claude.ai/api/mcp/auth_callback")
        assert redirect_allowed("http://127.0.0.1:33418/callback")
        assert redirect_allowed("http://localhost:5173/cb")
        assert not redirect_allowed("https://chatgpt.com/connector/oauth/")
        assert not redirect_allowed(_CHATGPT + "/more")
        assert not redirect_allowed(_CHATGPT + "?next=https://evil.example")
        assert not redirect_allowed(_CHATGPT + "#x")
        assert not redirect_allowed("https://chatgpt.com.evil.example/x")
        assert not redirect_allowed("https://evil.example/cb")
        assert not redirect_allowed("http://10.0.0.5/cb")
        assert redirect_allowed("https://my.example/cb",
                                extra=["https://my.example/cb"])


class TestTheCommandLine:
    def _run(self, *args, env=None):
        return subprocess.run(
            [sys.executable, "-m", "ogr_mcp", *args], cwd=str(_ROOT),
            env=env or _env(OGR_MCP_TOKEN=_TOKEN), capture_output=True,
            text=True, timeout=60)

    def test_the_rules_of_exposure(self):
        if not _have_mcp():
            return
        port = str(_free_port())
        http = ["--transport", "http", "--port", port]
        cases = [
            [*http, "--public-url", "https://x.example", "--no-auth"],
            [*http, "--public-url", "http://x.example"],
            [*http, "--tls-cert", "nope.pem"],
            [*http, "--oauth-redirect", "https://my.example/cb"],
            ["--public-url", "https://x.example"],          # stdio
        ]
        for args in cases:
            r = self._run(*args)
            assert r.returncode == 2, (args, r.stderr)
        # On the Internet the token must be long: anyone can try it.
        r = self._run(*http, "--public-url", "https://x.example",
                      env=_env(OGR_MCP_TOKEN="short-token"))
        assert r.returncode == 2 and "32" in r.stderr, r.stderr


class TestHttps:
    def test_tls_directly(self):
        if not _have_mcp():
            return
        try:
            import datetime as dt
            import ipaddress

            from cryptography import x509
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import ec
            from cryptography.x509.oid import NameOID
        except ImportError:
            return
        import tempfile
        key = ec.generate_private_key(ec.SECP256R1())
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,
                                             "127.0.0.1")])
        now = dt.datetime.now(dt.timezone.utc)
        cert = (x509.CertificateBuilder().subject_name(name)
                .issuer_name(name).public_key(key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(now - dt.timedelta(minutes=5))
                .not_valid_after(now + dt.timedelta(days=1))
                .add_extension(x509.SubjectAlternativeName(
                    [x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
                    critical=False)
                .add_extension(x509.BasicConstraints(ca=True,
                                                     path_length=None),
                               critical=True)
                .sign(key, hashes.SHA256()))
        with tempfile.TemporaryDirectory() as d:
            cert_f, key_f = Path(d) / "cert.pem", Path(d) / "key.pem"
            cert_f.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
            key_f.write_bytes(key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption()))
            import ssl
            ctx = ssl.create_default_context(cafile=str(cert_f))
            port = _free_port()
            base = f"https://127.0.0.1:{port}"
            proc = _start(port, "--tls-cert", str(cert_f), "--tls-key",
                          str(key_f), "--public-url", base,
                          scheme="https", verify=ctx)
            try:
                import httpx2
                meta = httpx2.get(f"{base}/.well-known/"
                                  "oauth-authorization-server",
                                  verify=ctx).json()
                assert meta["issuer"].rstrip("/") == base
                r = asyncio.run(_mcp_call(f"{base}/mcp", _TOKEN,
                                          verify=ctx))
                assert not r.is_error
            finally:
                _stop(proc)
