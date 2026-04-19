"""utils.network

Central network module.

Goals:
- Provide a single place to route *all* HTTP traffic through Tor or an authenticated proxy.

Supported routes:
- Tor SOCKS5 proxy at 127.0.0.1:<port> (socks5h)
- HTTP/HTTPS proxy in the form: host:port:user:pass (or host:port)

Note: Tor routing via requests requires PySocks ("requests[socks]" or "PySocks").
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Optional, Tuple
from urllib.parse import quote

import requests

_lock = threading.Lock()

_tor_enabled: bool = False
_tor_port: int = 9050

_proxy_enabled: bool = False
_proxy_raw: str = ""  # as pasted by user
_proxy_url: str = ""  # normalised url e.g. http://user:pass@host:port

# Cached session so we don't create a new TCP/TLS pool for every request
_session: Optional[requests.Session] = None
_session_cfg: Tuple = ()

_DEFAULT_UA = "NullWallet/1.0 (+https://example.invalid)"


@dataclass(frozen=True)
class RouteStatus:
    route: str  # "direct" | "tor" | "proxy"
    ip: str
    is_tor: Optional[bool] = None


# ── Configuration ───────────────────────────────────────────────────────────


def set_tor(enabled: bool, port: int = 9050):
    global _tor_enabled, _tor_port
    with _lock:
        _tor_enabled = bool(enabled)
        _tor_port = int(port) if port else 9050
        if _tor_enabled:
            # Avoid ambiguous routing; Tor and authenticated HTTP proxy together is confusing.
            _disable_proxy_locked()
        _reset_session()


def is_tor() -> bool:
    return _tor_enabled


def set_proxy(pasted: str, enabled: bool = True) -> Tuple[bool, str]:
    """Configure an HTTP/HTTPS proxy.

    pasted format: host:port:user:pass  (or host:port)

    Returns (ok, message).
    """
    global _proxy_enabled, _proxy_raw, _proxy_url

    with _lock:
        if not enabled:
            _disable_proxy_locked()
            _reset_session()
            return True, "Proxy disabled"

        pasted = (pasted or "").strip()
        if not pasted:
            return False, "Proxy string is empty"

        try:
            _proxy_url = _normalise_proxy(pasted)
            _proxy_raw = pasted
            _proxy_enabled = True
            # Avoid ambiguous routing
            _tor_enabled = False
            _reset_session()
            return True, "Proxy enabled"
        except Exception as e:
            return False, str(e)


def is_proxy() -> bool:
    return _proxy_enabled


def get_proxy_raw() -> str:
    return _proxy_raw


# ── Session / routing helpers ───────────────────────────────────────────────


def _disable_proxy_locked():
    global _proxy_enabled, _proxy_raw, _proxy_url
    _proxy_enabled = False
    _proxy_raw = ""
    _proxy_url = ""


def _reset_session():
    global _session, _session_cfg
    _session = None
    _session_cfg = ()


def _normalise_proxy(pasted: str) -> str:
    # Accept either "host:port" or "host:port:user:pass".
    parts = pasted.split(":")
    if len(parts) < 2:
        raise ValueError("Proxy must be at least host:port")

    host = parts[0].strip()
    port = parts[1].strip()
    if not host or not port:
        raise ValueError("Proxy host/port missing")

    # If extra colons exist, treat everything after the 3rd colon as password.
    user = passw = ""
    if len(parts) >= 4:
        user = parts[2]
        passw = ":".join(parts[3:])

    if user:
        user_q = quote(user, safe="")
        pass_q = quote(passw, safe="")
        return f"http://{user_q}:{pass_q}@{host}:{int(port)}"

    return f"http://{host}:{int(port)}"


def _active_route_locked() -> str:
    if _proxy_enabled and _proxy_url:
        return "proxy"
    if _tor_enabled:
        return "tor"
    return "direct"


def get_session() -> requests.Session:
    global _session, _session_cfg

    with _lock:
        route = _active_route_locked()
        cfg = (route, _tor_port, _proxy_url)

        if _session is not None and cfg == _session_cfg:
            return _session

        s = requests.Session()
        s.headers.update({"User-Agent": _DEFAULT_UA})

        if route == "tor":
            proxy = f"socks5h://127.0.0.1:{_tor_port}"
            s.proxies = {"http": proxy, "https": proxy}
        elif route == "proxy":
            # Use the same proxy for both protocols.
            s.proxies = {"http": _proxy_url, "https": _proxy_url}

        _session = s
        _session_cfg = cfg
        return s


def get(url: str, **kwargs) -> requests.Response:
    return get_session().get(url, **kwargs)


def post(url: str, **kwargs) -> requests.Response:
    return get_session().post(url, **kwargs)


# ── Diagnostics ─────────────────────────────────────────────────────────────


def check_connection() -> RouteStatus:
    """Return current route type and outward-facing IP.

    - If Tor is enabled, uses check.torproject.org and reports is_tor.
    - Otherwise uses ipify.
    """
    route = None
    with _lock:
        route = _active_route_locked()

    if route == "tor":
        try:
            r = get_session().get("https://check.torproject.org/api/ip", timeout=12)
            r.raise_for_status()
            data = r.json()
            return RouteStatus(route="tor", ip=data.get("IP", "unknown"), is_tor=bool(data.get("IsTor")))
        except Exception as e:
            return RouteStatus(route="tor", ip=str(e), is_tor=None)

    try:
        r = get_session().get("https://api.ipify.org?format=json", timeout=12)
        r.raise_for_status()
        ip = (r.json() or {}).get("ip", "unknown")
        return RouteStatus(route=route, ip=ip, is_tor=False)
    except Exception as e:
        return RouteStatus(route=route, ip=str(e), is_tor=None)
