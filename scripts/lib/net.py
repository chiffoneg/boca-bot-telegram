"""Pedidos HTTP con reintentos, usando solo la librería estándar (a
propósito: sin dependencias externas no hay nada que instalar ni que se
pueda romper con el tiempo)."""

import time
import urllib.error
import urllib.request

_ATTEMPTS = 3
RETRY_WAIT_SECONDS = 5


class NetError(Exception):
    """El pedido falló en todos los intentos."""


def request(url: str, data: bytes | None = None, headers: dict | None = None) -> bytes:
    # User-Agent por defecto de Python a propósito: ESPN rechaza con 403
    # cualquiera que contenga "bot".
    req = urllib.request.Request(url, data=data, headers=headers or {})

    last_error = None
    for attempt in range(1, _ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read()
        except (urllib.error.URLError, OSError) as exc:
            last_error = exc
            if attempt < _ATTEMPTS:
                time.sleep(RETRY_WAIT_SECONDS * attempt)

    # Sin la URL en el texto: en Telegram lleva el token del bot.
    raise NetError(f"{last_error}") from None
