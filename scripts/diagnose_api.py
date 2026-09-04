#!/usr/bin/env python3
"""Script de diagnóstico TEMPORAL, no forma parte del bot.

Prueba distintas formas de pedirle fixtures a API-Football para
entender qué permite realmente el plan free de esta cuenta. No manda
nada a Telegram ni toca data/next_match.json.
"""

import json
from datetime import datetime, timedelta, timezone

import requests

from lib import config

HEADERS = {"x-apisports-key": config.API_FOOTBALL_KEY}
BASE = config.API_FOOTBALL_BASE_URL


def call(label, path, params):
    print(f"\n{'=' * 60}\n{label}\nGET {path} params={params}")
    resp = requests.get(f"{BASE}{path}", headers=HEADERS, params=params, timeout=15)
    print(f"HTTP {resp.status_code}")
    try:
        data = resp.json()
    except ValueError:
        print(resp.text[:500])
        return
    print(f"errors: {data.get('errors')}")
    print(f"results: {data.get('results')}")
    resp_data = data.get("response")
    if isinstance(resp_data, list):
        print(f"response items: {len(resp_data)}")
        if resp_data:
            print(json.dumps(resp_data[0], ensure_ascii=False, indent=2)[:1500])
    else:
        print(json.dumps(resp_data, ensure_ascii=False, indent=2)[:1500])


def main():
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    in_3days = (now + timedelta(days=3)).date().isoformat()

    call("STATUS de la cuenta", "/status", {})

    call(
        "fixtures por date (sin team ni season)",
        "/fixtures",
        {"date": today},
    )

    call(
        "fixtures por team + date (sin season)",
        "/fixtures",
        {"team": config.BOCA_TEAM_ID, "date": today},
    )

    call(
        "fixtures por team + from/to + season actual",
        "/fixtures",
        {"team": config.BOCA_TEAM_ID, "from": today, "to": in_3days, "season": now.year},
    )

    call(
        "fixtures por team + from/to SIN season",
        "/fixtures",
        {"team": config.BOCA_TEAM_ID, "from": today, "to": in_3days},
    )


if __name__ == "__main__":
    main()
