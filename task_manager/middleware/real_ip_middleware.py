# task_manager/middleware/real_ip_middleware.py

import logging

logger = logging.getLogger(__name__)


class RealIPMiddleware:
    """
    Inserts the client's real IP into REMOTE_ADDR.

    Nginx passes the real IP via the X-Real-IP header.
    Without this middleware, Django sees the Docker gateway IP (172.x.x.x),
    not the client's real IP.

    Works only if the request came from a trusted proxy
    in the TRUSTED_PROXIES list in settings.py.

    In development mode (TRUSTED_PROXIES not set) — does nothing.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.conf import settings

        trusted_proxies = getattr(settings, 'TRUSTED_PROXIES', set())

        if trusted_proxies:
            remote_addr = request.META.get('REMOTE_ADDR', '')

            if remote_addr in trusted_proxies:
                # X-Real-IP — most reliable option.
                # Nginx sets it explicitly:
                # proxy_set_header X-Real-IP $remote_addr
                # $remote_addr in nginx is always the IP of whoever
                # connected to nginx, it cannot be spoofed from the browser
                # (unlike X-Forwarded-For).
                real_ip = request.META.get('HTTP_X_REAL_IP', '').strip()

                if not real_ip:
                    # Fallback to X-Forwarded-For.
                    # Format: "real_client, proxy1, proxy2"
                    # Take the first element — this is the real client's IP.
                    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
                    if forwarded_for:
                        real_ip = forwarded_for.split(',')[0].strip()

                if real_ip:
                    request.META['REMOTE_ADDR'] = real_ip

        return self.get_response(request)
