"""Client IP extraction with an explicit trusted-proxy boundary."""

from ipaddress import ip_address, ip_network

from fastapi import Request

from app.config import settings


def _trusted_proxy_ips() -> set[str]:
    return {value.strip() for value in settings.trusted_proxy_ips.split(",") if value.strip()}


def _is_trusted_proxy(value: str) -> bool:
    try:
        direct_ip = ip_address(value)
    except ValueError:
        return False
    for configured in _trusted_proxy_ips():
        try:
            if direct_ip in ip_network(configured, strict=False):
                return True
        except ValueError:
            continue
    return False


def get_client_ip(request: Request) -> str:
    """Use X-Forwarded-For only when the direct peer is trusted."""

    direct_peer = request.client.host if request.client else "unknown"
    if _is_trusted_proxy(direct_peer):
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
    return direct_peer
