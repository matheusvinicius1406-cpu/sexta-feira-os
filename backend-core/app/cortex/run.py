"""
run_intent — executa a intenção nas engines reais do kernel.

Cada handler pega a intenção (verb/target/params), chama a engine certa e
devolve um texto honesto do que aconteceu. Nenhum handler chama LLM: a
decisão é a intenção, a execução é a engine, a resposta é a persona.
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.api.routers.radio import get_radio
from app.core.di import get_memory, get_planning, get_voice
from app.cortex.intent import Intent

logger = logging.getLogger("sexta-feira.cortex")

_YN = {"não": False, "nao": False, "no": False, "desligado": False, "off": False}


def _radio():
    return get_radio()


def _voice():
    return get_voice()


# ── handlers ──────────────────────────────────────────────


async def _tocar(db, owner_id, it: Intent) -> str:
    radio = _radio()
    q = (it.target or "").strip()
    if not q:
        return "O que você quer que eu toque?"
    try:
        result = await radio.play_search(q)
    except Exception as e:  # noqa: BLE001
        return f"Não consegui buscar '{q}': {e}"
    tracks = result.get("tracks") or []
    if not tracks:
        return f"Nada encontrado para '{q}'."
    first = tracks[0]
    try:
        await radio.play_radio_station(first["stream_url"], first["title"]) \
            if first.get("stream_url") else await radio.play_youtube_video(first["id"])
    except Exception as e:  # noqa: BLE001
        return f"Encontrei '{first['title']}' mas não consegui tocar: {e}"
    return f"Tocando {first['title']}."


async def _colar(db, owner_id, it: Intent) -> str:
    radio = _radio()
    url = (it.target or "").strip()
    if "youtu" in url and ("watch" in url or "be/" in url or "shorts" in url):
        from urllib.parse import parse_qs, urlparse
        vid = parse_qs(urlparse(url).query).get("v", [None])[0]
        if not vid and "be/" in url:
            vid = url.split("be/")[-1].split("?")[0]
        track = await radio.play_youtube_video(vid) if vid else None
        if track:
            return f"Tocando {track.title}."
        return "Não consegui extrair o stream deste vídeo."
    track = await radio.play_radio_station(url, "Link colado")
    return f"Tocando {track.title}."


async def _volume(db, owner_id, it: Intent) -> str:
    radio = _radio()
    lvl = it.params.get("target")
    if lvl is not None:  # "volume 50"
        try:
            n = max(0, min(100, int(lvl)))
        except ValueError:
            return "Volume precisa ser um número de 0 a 100."
        radio.set_volume(n / 100)
        return f"Volume em {n}%."
    cur = (radio.get_state().get("volume") or 0.8) * 100
    if "aumenta" in it.raw or "sobe" in it.raw:
        n = min(100, round(cur) + 10)
    else:
        n = max(0, round(cur) - 10)
    radio.set_volume(n / 100)
    return f"Volume em {n}%."


async def _pular(db, owner_id, it: Intent) -> str:
    t = _radio().skip()
    return f"Pulei para {t.title}." if t else "A fila acabou."


async def _parar(db, owner_id, it: Intent) -> str:
    # O kernel não controla reprodução client-side; honesto: esvazia a fila.
    _radio().clear_queue()
    return "Fila limpa. A reprodução para quando a faixa atual terminar."


async def _salvar_playlist(db, owner_id, it: Intent) -> str:
    count = _radio().save_playlist((it.target or "").strip())
    if not count:
        return "Nada para salvar: a fila está vazia."
    return f"Playlist '{it.target}' salva com {count} faixa(s)."


async def _modo(db, owner_id, it: Intent) -> str:
    radio = _radio()
    m = (it.target or "").lower()
    if "embaralhar" in m:
        on = radio.toggle_shuffle()
        return f"Embaralhar {'ligado' if on else 'desligado'}."
    if "repetir" in m:
        on = radio.toggle_repeat()
        return f"Repetir {'ligado' if on else 'desligado'}."
    if "adblock" in m:
        on = radio.toggle_ad_blocker()
        return f"Adblock {'ligado' if on else 'desligado'}."
    return "Modo não reconhecido."


async def _voz(db, owner_id, it: Intent) -> str:
    want = (it.target or "").strip().lower()
    if not want:
        return "Qual voz? Disponíveis: jarvis, friendly, military, ultron, alfred."
    from app.voice.voice_packs import list_packs
    packs = {str(p["key"]).lower(): p for p in list_packs()}
    if want not in packs:
        return f"Voz '{want}' não encontrada. Disponíveis: {', '.join(packs)}."
    _voice().set_pack(want)
    return f"Voz trocada para {packs[want]['name']}."


async def _falar(db, owner_id, it: Intent) -> str:
    # O texto a falar volta como resposta — o router decide o áudio.
    return it.target or ""


async def _guardar(db, owner_id, it: Intent) -> str:
    content = (it.target or "").strip()
    if not content:
        return "O que você quer que eu guarde?"
    m = await get_memory().remember(db, owner_id, content, kind="fact", source="voice")
    return f"Guardado: {m.content}"


async def _esquecer(db, owner_id, it: Intent) -> str:
    q = (it.target or "").strip()
    if not q:
        return "O que você quer que eu esqueça?"
    hits = await get_memory().recall_graph(db, owner_id, q)
    if not hits:
        return f"Não achei nada parecido com '{q}' na memória."
    top = hits[0]
    get_memory().forget(db, owner_id, top.id)
    return f"Esquecido: {top.content}"


async def _criar_meta(db, owner_id, it: Intent) -> str:
    title = (it.target or "").strip()
    if not title:
        return "Qual é a meta?"
    g = await get_planning().create_goal(db, owner_id, title)
    return f"Meta criada: {g.title}"


async def _concluir_meta(db, owner_id, it: Intent) -> str:
    title = (it.target or "").strip()
    goals = get_planning().list_goals(db, owner_id, status="active")
    hit = next((g for g in goals if title.lower() in (g.title or "").lower()), None)
    if not hit:
        return f"Meta '{title}' não encontrada entre as ativas."
    await get_planning().complete_goal(db, owner_id, hit.id)
    return f"Meta concluída: {hit.title}"


async def _hora(db, owner_id, it: Intent) -> str:
    now = datetime.now()
    return now.strftime("São %H:%M de %d/%m/%Y.")


async def _status(db, owner_id, it: Intent) -> str:
    radio = get_radio()
    s = radio.get_state()
    cur = s.get("current_track")
    parts = []
    if cur:
        parts.append(f"tocando {cur.get('title', '')}")
    parts.append(f"fila {s.get('queue_length', 0)}")
    try:
        from app.core.di import get_memory as _gm
        mems = _gm().count(db, owner_id) if hasattr(_gm(), "count") else None
        if mems is not None:
            parts.append(f"{mems} memórias")
    except Exception:  # noqa: BLE001
        pass
    return "Sistema nominal — " + ", ".join(parts) + "."


_HANDLERS = {
    "tocar_playlist": _tocar,
    "tocar_preset": _tocar,
    "tocar": _tocar,
    "colar": _colar,
    "volume": _volume,
    "pular": _pular,
    "parar": _parar,
    "salvar_playlist": _salvar_playlist,
    "modo": _modo,
    "voz": _voz,
    "falar": _falar,
    "guardar": _guardar,
    "esquecer": _esquecer,
    "criar_meta": _criar_meta,
    "concluir_meta": _concluir_meta,
    "hora": _hora,
    "status": _status,
}


async def run_intent(db: Session, owner_id: str, it: Intent) -> str:
    """Executa a intenção e devolve o texto do resultado. Nunca chama LLM."""
    handler = _HANDLERS.get(it.verb)
    if handler is None:
        return f"Não sei executar '{it.verb}' ainda."
    try:
        return await handler(db, owner_id, it)
    except Exception as e:  # noqa: BLE001 — a falha vira resposta honesta
        logger.warning("cortex '%s' falhou: %s", it.verb, e)
        return f"Não consegui: {e}"
