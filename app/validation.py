"""Validation rules for URLs submitted to the service."""

import ipaddress
import socket
from urllib.parse import urlsplit


LOCAL_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
}


def _is_non_public_ip(host: str) -> bool:
    """Return true for loopback, private, reserved, or otherwise non-public IPs."""

    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False

    # is_global is deliberately used as the final check so ranges such as
    # link-local and carrier-grade NAT are not accidentally accepted.
    return not address.is_global


def _points_to_non_public_host(host: str) -> bool:
    normalized_host = host.rstrip(".").lower()
    if (
        normalized_host in LOCAL_HOSTNAMES
        or normalized_host.endswith(".localhost")
        or normalized_host.endswith(".local")
    ):
        return True

    if _is_non_public_ip(normalized_host):
        return True

    # Hostnames can resolve to private addresses even when the URL contains
    # no literal IP. If DNS is unavailable, leave the decision to the caller;
    # the explicit local names and literal IP checks above remain deterministic.
    try:
        resolved_addresses = {
            result[4][0]
            for result in socket.getaddrinfo(normalized_host, None, type=socket.SOCK_STREAM)
        }
    except (socket.gaierror, OSError):
        return False

    return any(_is_non_public_ip(address) for address in resolved_addresses)


def validate_long_url(value: str, base_url: str) -> str:
    """Validate and normalize a destination URL for a short link."""

    candidate = value.strip()
    parts = urlsplit(candidate)

    if parts.scheme.lower() not in {"http", "https"}:
        raise ValueError("URL must use http:// or https://")
    if not parts.hostname:
        raise ValueError("URL must include a hostname")

    host = parts.hostname.rstrip(".").lower()
    own_host = urlsplit(base_url).hostname
    if own_host:
        own_host = own_host.rstrip(".").lower()
        if host == own_host or host.endswith(f".{own_host}"):
            raise ValueError("URL cannot point to this shortener's own domain")

    if _points_to_non_public_host(host):
        raise ValueError("URL cannot point to localhost or a private IP address")

    return candidate
