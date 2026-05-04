# task_manager/middleware/real_ip_middleware.py

import logging

logger = logging.getLogger(__name__)


class RealIPMiddleware:
    """
    Подставляет реальный IP клиента в REMOTE_ADDR.

    Nginx передаёт реальный IP через заголовок X-Real-IP.
    Без этого middleware Django видит IP шлюза Docker (172.x.x.x),
    а не реальный IP клиента.

    Работает только если запрос пришёл от доверенного прокси
    из списка TRUSTED_PROXIES в settings.py.

    В режиме разработки (TRUSTED_PROXIES не задан) — не делает ничего.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.conf import settings

        trusted_proxies = getattr(settings, 'TRUSTED_PROXIES', set())

        if trusted_proxies:
            remote_addr = request.META.get('REMOTE_ADDR', '')

            if remote_addr in trusted_proxies:
                # X-Real-IP — самый надёжный вариант.
                # Nginx выставляет его явно:
                # proxy_set_header X-Real-IP $remote_addr
                # $remote_addr в nginx — это всегда IP того,
                # кто подключился к nginx, его нельзя подделать из браузера
                # (в отличие от X-Forwarded-For).
                real_ip = request.META.get('HTTP_X_REAL_IP', '').strip()

                if not real_ip:
                    # Fallback на X-Forwarded-For.
                    # Формат: "реальный_клиент, прокси1, прокси2"
                    # Берём первый элемент — это IP реального клиента.
                    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
                    if forwarded_for:
                        real_ip = forwarded_for.split(',')[0].strip()

                if real_ip:
                    request.META['REMOTE_ADDR'] = real_ip

        return self.get_response(request)
