"""Cliente mínimo para mandar mensajes por la API de Telegram."""

import requests

from . import config


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
        resp = requests.post(url, json=payload, timeout=15)
    except requests.RequestException as exc:
        raise TelegramError(f"Error de red mandando mensaje a Telegram: {exc}") from exc

    if resp.status_code != 200:
        raise TelegramError(
            f"Telegram respondió HTTP {resp.status_code}: {resp.text[:300]}"
        )


def send_photo(photo_bytes: bytes, caption: str | None = None) -> None:
    config.validate_telegram_config()

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendPhoto"
    data = {"chat_id": config.TELEGRAM_CHAT_ID}
    if caption:
        data["caption"] = caption
    files = {"photo": ("alineaciones.png", photo_bytes, "image/png")}

    try:
        resp = requests.post(url, data=data, files=files, timeout=30)
    except requests.RequestException as exc:
        raise TelegramError(f"Error de red mandando foto a Telegram: {exc}") from exc

    if resp.status_code != 200:
        raise TelegramError(
            f"Telegram respondió HTTP {resp.status_code}: {resp.text[:300]}"
        )
