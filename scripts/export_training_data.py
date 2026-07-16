#!/usr/bin/env python3
"""
Export YOUR history into a fine-tuning dataset (chat JSONL).

Usage (from backend-core/, with the venv active):
    python ../scripts/export_training_data.py --out ../data/dataset.jsonl

The output feeds scripts/finetune_lora.py. It reads only your local DB and
writes a local file. Nothing leaves the machine.
"""
import argparse
import sys
from pathlib import Path

# Allow running from repo root or backend-core/
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend-core"))

from app.db.database import SessionLocal  # noqa: E402
from app.models.models import Owner  # noqa: E402
from app.brain.teach import build_dataset, to_jsonl  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/dataset.jsonl", help="output JSONL path")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        owner = db.query(Owner).first()
        if not owner:
            print("Nenhum dono configurado ainda. Suba o kernel uma vez com OWNER_* no .env.")
            sys.exit(1)
        samples = build_dataset(db, owner.id)
    finally:
        db.close()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for line in to_jsonl(samples):
            f.write(line + "\n")

    print(f"✅ {len(samples)} amostras exportadas para {out}")
    if len(samples) < 200:
        print("ℹ️  Poucas amostras ainda. Converse mais com o Sexta-Feira e adicione "
              "memórias antes de treinar — fine-tuning gosta de volume e qualidade.")


if __name__ == "__main__":
    main()
