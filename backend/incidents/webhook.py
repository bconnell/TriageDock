"""Validate configured outbound destinations; no user-provided URL is accepted."""
import ipaddress
from urllib.parse import urlsplit
from django.core.exceptions import ImproperlyConfigured


def validate_webhook_url(url):
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ImproperlyConfigured("Invalid notification webhook URL") from exc
    if (parsed.scheme != "https" or not host or parsed.username or parsed.password
            or parsed.fragment or (port is not None and port != 443)):
        raise ImproperlyConfigured("Webhook requires HTTPS, a host, and no credentials or redirect fragment")
    host = host.rstrip(".").lower()
    if host in {"localhost", "metadata.google.internal"} or host.endswith((".local", ".localhost", ".internal")):
        raise ImproperlyConfigured("Webhook host must not be local or internal")
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        if "." not in host:
            raise ImproperlyConfigured("Webhook host must be fully qualified")
    else:
        if not addr.is_global:
            raise ImproperlyConfigured("Webhook host must not be private or reserved")
    return host
