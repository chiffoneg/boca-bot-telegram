"""Cliente mínimo para mandar mensajes por la API de Telegram."""

import json

from . import config, net


class TelegramError(Exception):
    pass


def send_message(text: str) -> None:
    config.validate_telegram_config()

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": True,
        # Sin parse_mode a propósito: texto plano, sin formato Markdown/HTML,
        # para que sea copiable tal cual a WhatsApp.
    }

    try:
        net.request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
    except net.NetError as exc:
        raise TelegramError(f"Error mandando mensaje a Telegram: {exc}") from exc
