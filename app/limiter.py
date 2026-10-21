"""Per-client rate limiting (spec §10 #18; F011, F062, F007, F054).

The key is the visitor's address, chosen so a client cannot pick it (F011). Render's proxy
appends the address it saw to X-Forwarded-For, so the rightmost hop is the one entry a client
cannot write. When that hop is a Cloudflare edge, CF-Connecting-IP (which Cloudflare
overwrites) is the visitor. Otherwise the rightmost hop is the visitor, and any
CF-Connecting-IP the client sent is ignored. With no usable X-Forwarded-For, the socket peer.
A candidate that does not parse as an IP address moves on to the next one. IPv6 visitors are
keyed by their /64 (the block one subscriber gets), IPv4-mapped IPv6 by the IPv4 address.

Buckets are per route, not per URL (key_style="endpoint", F062), so varying a ZIP or a bill
number does not start a fresh count. Routes without a limit of their own share one site-wide
per-client limit (CV_SITE_RATE_LIMIT, default 600/minute, F007). /static, /favicon.ico,
/robots.txt, /api/health and paths no route matches are exempt."""
import hashlib
import ipaddress
import logging
import os

from limits import parse_many
from slowapi import Limiter
from starlette.requests import Request

logger = logging.getLogger(__name__)

# Cloudflare's published edge ranges, from https://www.cloudflare.com/ips-v4 and
# https://www.cloudflare.com/ips-v6 (2026-10-21). A range missing here only keys visitors
# behind it by the edge address; it never lets a client choose its own key.
_CLOUDFLARE_NETWORKS = tuple(ipaddress.ip_network(net) for net in (
    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22",
    "141.101.64.0/18", "108.162.192.0/18", "190.93.240.0/20", "188.114.96.0/20",
    "197.234.240.0/22", "198.41.128.0/17", "162.158.0.0/15", "104.16.0.0/13",
    "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22",
    "2400:cb00::/32", "2606:4700::/32", "2803:f800::/32", "2405:b500::/32",
    "2405:8100::/32", "2a06:98c0::/29", "2c0f:f248::/32",
))


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


def client_key(request: Request) -> str:
    hops = ",".join(request.headers.getlist("x-forwarded-for")).split(",")
    proxy_saw = _parse_ip(hops[-1])  # the hop Render's proxy appended
    if proxy_saw is not None:
        if any(proxy_saw in network for network in _CLOUDFLARE_NETWORKS):
            visitor = _parse_ip(request.headers.get("cf-connecting-ip", ""))
            if visitor is not None:
                return _bucket(visitor)
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
