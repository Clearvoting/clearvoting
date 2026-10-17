"""Per-client rate limiting (spec §10 #18).

Behind Cloudflare and Render's proxy every request arrives from a proxy address, so keying on
the socket peer put every visitor in one shared bucket. The key is the client address the edge
reports: CF-Connecting-IP, else the first X-Forwarded-For entry, else the socket peer. Spoofing
the header can only evade a limit, which is no worse than one shared bucket."""
from slowapi import Limiter
from starlette.requests import Request


def client_key(request: Request) -> str:
    cf_ip = request.headers.get("cf-connecting-ip", "").strip()
    if cf_ip:
        return cf_ip
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded:
        return forwarded
    return request.client.host if request.client else "127.0.0.1"


limiter = Limiter(key_func=client_key)
