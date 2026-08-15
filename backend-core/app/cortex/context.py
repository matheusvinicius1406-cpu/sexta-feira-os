"""
Context — o snapshot do mundo que as regras avaliam.

Cada fonte é opcional e honesta: se a engine não está disponível, o campo
simplesmente não entra no contexto e a condição que depender dele falha na
trilha com "(indisponível)". O cortex nunca inventa um número para a regra
acender.
"""
from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger("sexta-feira.cortex.context")

_WEEKDAYS = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]


def _safe(fn, default=None):
    """Executa uma leitura de engine; qualquer falha vira o default — o
    contexto nunca derruba a avaliação por causa de um sensor ruim."""
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        logger.debug("contexto: fonte indisponível: %s", e)
        return default


async def build_context(db, owner_id: str) -> dict:
    """Monta o snapshot do mundo. `db`/`owner_id` podem ser None — as fontes
    que dependem deles (metas, memórias) ficam ausentes nesse caso."""
    now = datetime.now()
    ctx: dict = {
        "agora": {
            "hora": now.hour,
            "dia_semana": _WEEKDAYS[now.weekday()],
            "data_iso": now.date().isoformat(),
        },
    }

    # Rádio (singleton do router — mesmo estado que o painel mostra).
    try:
        from app.api.routers.radio import get_radio
        state = _safe(get_radio().get_state)
        if state:
            cur = state.get("current_track") or {}
            ctx["radio"] = {
                "tocando": bool(state.get("is_playing")) and bool(cur),
                "faixa": (cur.get("title") or "").strip() or None,
                "fila": int(state.get("queue_length") or 0),
                "volume": state.get("volume"),
                "shuffle": bool(state.get("shuffle")),
                "repeat": bool(state.get("repeat")),
            }
    except Exception as e:  # noqa: BLE001
        logger.debug("contexto: rádio indisponível: %s", e)

    # Voz ativa (pack key — o mesmo que `usar voz <nome>` troca).
    try:
        from app.core.di import get_voice
        from app.voice.voice_packs import VOICE_PACKS
        voice = _safe(get_voice)
        if voice:
            pack = voice.pack
            key = next((k for k, p in VOICE_PACKS.items() if p is pack or p.name == pack.name), None)
            ctx["voz"] = {"pack": key or pack.name.lower()}
    except Exception as e:  # noqa: BLE001
        logger.debug("contexto: voz indisponível: %s", e)

    # Sistema (CPU % instantânea — psutil, mesma fonte do painel System).
    try:
        import psutil
        cpu = _safe(lambda: psutil.cpu_percent(interval=None))
        if cpu is not None:
            ctx["sistema"] = {"cpu_percent": round(float(cpu), 1)}
    except Exception as e:  # noqa: BLE001
        logger.debug("contexto: sistema indisponível: %s", e)

    # Fontes que dependem do banco: metas, memórias, mundo, timer, marcadores.
    if db is not None and owner_id:
        try:
            from app.core.di import (
                get_briefing,
                get_memory,
                get_planning,
                get_timetracker,
                get_world,
            )

            planning = _safe(get_planning)
            if planning:
                ativas = _safe(lambda: len(planning.list_goals(db, owner_id, status="active")), 0)
                if ativas is not None:
                    ctx.setdefault("metas", {})["ativas"] = int(ativas)

            memory = _safe(get_memory)
            if memory:
                from app.models.models import Memory
                total = _safe(lambda: db.query(Memory).filter(Memory.owner_id == owner_id).count(), 0)
                if total is not None:
                    ctx.setdefault("memoria", {})["total"] = int(total)
                # Fatia recente (título + conteúdo) para o operador `memoria_tem`
                recentes = _safe(lambda: memory.list_all(db, owner_id, limit=30), [])
                if recentes:
                    ctx.setdefault("memoria", {})["recentes"] = [
                        {"titulo": m.title, "conteudo": m.content}
                        for m in recentes
                        if getattr(m, "content", None)
                    ]
                # Marcadores: memórias de kind=bookmark (o Browser·Marks usa o mesmo critério)
                marks = [m for m in (recentes or []) if getattr(m, "kind", None) == "bookmark"]
                if marks:
                    ctx["marcadores"] = {
                        "total": len(marks),
                        "itens": [
                            {"titulo": m.title, "url": m.content}
                            for m in marks[:20]
                            if getattr(m, "content", None)
                        ],
                    }

            # Mundo — os fatos do AGORA (chave → valor), para `fato_igual`/`fato_existe`.
            world = _safe(get_world)
            if world:
                facts = _safe(lambda: world.snapshot(db, owner_id, limit=50), [])
                if facts:
                    ctx["mundo"] = {
                        "fatos": {f.key: f.value for f in facts if getattr(f, "key", None)}
                    }

            # Timer — o aberto, para `timer_rodando`/`timer_label`.
            tracker = _safe(get_timetracker)
            if tracker:
                cur = _safe(lambda: tracker.current(db, owner_id))
                ctx["timetrack"] = {
                    "rodando": cur is not None,
                    "label": getattr(cur, "label", None) if cur else None,
                }

            # Briefing — já foi gerado hoje? (rotina matinal honesta: só sugere
            # se ainda não existe report do dia.)
            briefing = _safe(get_briefing)
            if briefing:
                latest = _safe(lambda: briefing.latest(db, owner_id))
                if latest is not None:
                    ctx["briefing"] = {"hoje": latest.created_at.date() == now.date()}
        except Exception as e:  # noqa: BLE001
            logger.debug("contexto: banco indisponível: %s", e)

    return ctx
