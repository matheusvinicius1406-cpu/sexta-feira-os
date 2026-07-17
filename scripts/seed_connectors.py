#!/usr/bin/env python3
"""
Seed a starter pack of FREE, no-auth API capabilities.

This is the first drop of the "giant API system" — a handful of public APIs (from
the spirit of github.com/public-apis) that work with zero keys, so the brain can
act out of the box. Add thousands more via POST /api/v1/connectors.

Usage (from backend-core/, venv active, after the kernel created your owner):
    python ../scripts/seed_connectors.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend-core"))

from app.connectors.service import ConnectorService  # noqa: E402
from app.connectors.vault import Vault  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.models.models import Owner  # noqa: E402

STARTER: list[dict] = [
    {
        "name": "current_time",
        "description": "Hora e data atuais de um fuso (ex.: America/Sao_Paulo).",
        "category": "time",
        "url": "https://worldtimeapi.org/api/timezone/{timezone}",
        "params_schema": [{"name": "timezone", "description": "ex.: America/Sao_Paulo", "required": True}],
    },
    {
        "name": "weather_now",
        "description": "Clima atual por latitude/longitude (Open-Meteo).",
        "category": "weather",
        "url": "https://api.open-meteo.com/v1/forecast",
        "query": {"latitude": "{lat}", "longitude": "{lon}", "current_weather": "true"},
        "params_schema": [
            {"name": "lat", "required": True}, {"name": "lon", "required": True},
        ],
    },
    {
        "name": "currency_convert",
        "description": "Converte moedas (ex.: USD -> BRL).",
        "category": "finance",
        "url": "https://api.exchangerate.host/convert",
        "query": {"from": "{from}", "to": "{to}", "amount": "{amount}"},
        "params_schema": [
            {"name": "from", "required": True}, {"name": "to", "required": True},
            {"name": "amount", "required": False},
        ],
    },
    {
        "name": "define_word",
        "description": "Definição de uma palavra em inglês.",
        "category": "reference",
        "url": "https://api.dictionaryapi.dev/api/v2/entries/en/{word}",
        "params_schema": [{"name": "word", "required": True}],
    },
    {
        "name": "iss_location",
        "description": "Posição atual da Estação Espacial Internacional.",
        "category": "space",
        "url": "http://api.open-notify.org/iss-now.json",
    },
]


def main() -> None:
    db = SessionLocal()
    try:
        owner = db.query(Owner).first()
        if not owner:
            print("Nenhum dono configurado. Suba o kernel uma vez com OWNER_* no .env.")
            sys.exit(1)
        service = ConnectorService(Vault())
        for spec in STARTER:
            service.upsert_capability(db, owner.id, spec)
        print(f"✅ {len(STARTER)} capacidades semeadas. Veja em GET /api/v1/connectors.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
