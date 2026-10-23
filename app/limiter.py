"""Per-client rate limiting (spec §10 #18; F011, F062, F007, F054).

The key is the visitor's address (F011). CF-Connecting-IP comes first: Cloudflare overwrites
it, so a client cannot set it through Cloudflare. Without it, the rightmost X-Forwarded-For
entry (the hop the nearest proxy appended; entries left of it are client-written), then the
socket peer. The key does not depend on which proxy hops sit between Cloudflare and the app,
so a Render hop cannot fold every visitor into one bucket. Traffic sent straight to the
origin can set CF-Connecting-IP; the shared cap on the write routes below bounds what that
can do, and CV_ORIGIN_SECRET (see _from_cloudflare) closes it once it is set. A candidate
that does not parse as an IP address moves on to the next one. IPv6
visitors are keyed by their /64 (the block one subscriber gets), IPv4-mapped IPv6 by the
IPv4 address.

Buckets are per route, not per URL (key_style="endpoint", F062), so varying a ZIP or a bill
number does not start a fresh count. Routes without a limit of their own share one site-wide
per-client limit (CV_SITE_RATE_LIMIT, default 600/minute, F007). /static, /favicon.ico,
/robots.txt, /api/health and paths no route matches are exempt."""
import hashlib
import hmac
import ipaddress
import logging
import os

from limits import parse_many
from slowapi import Limiter
from starlette.requests import Request

logger = logging.getLogger(__name__)


def _parse_ip(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        address = ipaddress.ip_address(value.strip())
    except ValueError:
        return None
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        return address.ipv4_mapped
    return address


def _bucket(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> str:
    if isinstance(address, ipaddress.IPv6Address):
        return str(ipaddress.IPv6Network((int(address), 64), strict=False))
    return str(address)


# Opt-in proof that a request came through Cloudflare (F011). A Cloudflare Transform Rule adds
# X-Origin-Auth: <secret> to every request it forwards, and CV_ORIGIN_SECRET holds the same value
# on Render. Unset (the default), CF-Connecting-IP counts whenever it is an address. Set, it counts
# only on requests carrying the secret, so traffic sent straight to the origin is keyed by the hop
# Render's proxy appended. Add the Cloudflare rule first, confirm it reaches the app, then set it.
ORIGIN_SECRET_HEADER = "x-origin-auth"


def _from_cloudflare(request: Request) -> bool:
    secret = os.environ.get("CV_ORIGIN_SECRET", "")
    if not secret:
        return True
    return hmac.compare_digest(request.headers.get(ORIGIN_SECRET_HEADER, "").encode(), secret.encode())


def client_key(request: Request) -> str:
    visitor = _parse_ip(request.headers.get("cf-connecting-ip", "")) if _from_cloudflare(request) else None
    if visitor is not None:
        return _bucket(visitor)  # Cloudflare overwrites it, so through Cloudflare no client sets it
    hops = ",".join(request.headers.getlist("x-forwarded-for")).split(",")
    proxy_saw = _parse_ip(hops[-1])  # the hop the nearest proxy appended
    if proxy_saw is not None:
        return _bucket(proxy_saw)
    peer = request.client.host if request.client else "127.0.0.1"
    address = _parse_ip(peer)
    return _bucket(address) if address is not None else peer


# The write routes also carry a cap every client shares (F011): no number of addresses can
# write more rows than this into the Google Sheet, whose service account allows 60 writes a
# minute. 25 a minute on each route keeps the two together under that.
ALL_CLIENTS = "all-clients"


def all_clients() -> str:
    return ALL_CLIENTS


DEFAULT_SITE_LIMIT = "600/minute"


def _site_limit(value: str | None) -> str:
    """CV_SITE_RATE_LIMIT, e.g. "600/minute". A value the limiter cannot parse would fail
    every request inside it, so that is logged and the default is used instead."""
    if not value or not value.strip():
        return DEFAULT_SITE_LIMIT
    try:
        parse_many(value)
    except ValueError:
        logger.error("CV_SITE_RATE_LIMIT=%r is not a rate limit; using %s", value, DEFAULT_SITE_LIMIT)
        return DEFAULT_SITE_LIMIT
    return value.strip()


# slowapi logs each refusal as "ratelimit <limit> (<key>) exceeded at endpoint: <route>", and
# the key is the visitor's address (F054). The filter swaps it for a short hash salted per
# process: one client's repeats still read as one client, and the address is never written.
_LOG_SALT = os.urandom(16)


class _HashClientKey(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if (isinstance(args, tuple) and len(args) == 3 and str(record.msg).startswith("ratelimit ")
                and args[1] != ALL_CLIENTS):
            digest = hashlib.sha256(_LOG_SALT + str(args[1]).encode()).hexdigest()[:10]
            record.args = (args[0], f"client {digest}", args[2])
        return True


logging.getLogger("slowapi").addFilter(_HashClientKey())

limiter = Limiter(key_func=client_key, key_style="endpoint",
                  application_limits=[_site_limit(os.environ.get("CV_SITE_RATE_LIMIT"))])
