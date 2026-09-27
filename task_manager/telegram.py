import json
import logging
import urllib.request

import os

from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)

# Bot API may be unreachable from some networks (e.g. some
# hosting providers block or throttle api.telegram.org),
# so keep the timeout short to avoid tying up gunicorn workers.
TELEGRAM_TIMEOUT_SECONDS = 10


def is_telegram_feedback_configured():
    return bool(os.getenv('TELEGRAM_BOT_TOKEN')
                and os.getenv('TELEGRAM_CHAT_ID'))


def send_feedback_to_telegram(text):
    """Send a feedback message via the Bot API.

    Returns (True, None) on success, (False, error_message) on failure.
    Never raises: feedback sending must not break the page for the user.
    """
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        return False, _("Feedback sending is not configured.")

    url = (f"https://api.telegram.org/bot{token}/sendMessage")
    payload = json.dumps({
        'chat_id': chat_id,
        'text': text,
    }).encode('utf-8')
    request = urllib.request.Request(
        url,
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(request,
                                    timeout=TELEGRAM_TIMEOUT_SECONDS) as r:
            response = json.loads(r.read().decode('utf-8'))
        if response.get('ok'):
            return True, None
        return False, _("Failed to send message to Telegram.")
    except (urllib.error.URLError, OSError, ValueError):
        logger.exception('Telegram feedback sending failed')
        return False, _("Failed to send message to Telegram. "
                        "Please try again later.")
