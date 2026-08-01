"""
The built-in automation catalog — what the Teia can do for you on day one.

Ten automations, written as plain Python `Workflow` objects, that use only local
capabilities: no API key, no account, nothing leaving the machine. They are
seeded (disabled ones included) on first boot and are ordinary workflows
afterwards — edit them, disable them, delete them.

Each builder returns `(workflow, description, tags, enabled)`. Anything that
would nag the owner unprompted ships DISABLED; the quiet, useful ones ship on.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.automation.teia.domain.graph import Workflow

logger = logging.getLogger("sexta-feira.teia.catalog")


# ---------------------------------------------------------------- builders


def briefing_matinal() -> Workflow:
    """07:00 — generate the daily briefing and read it to the owner."""
    wf = Workflow(name="Briefing matinal")
    report = wf.add_node("briefing", {"tipo": "daily"}, id="briefing")
    notify = wf.add_node(
        "notificar",
        {"texto": "Bom dia. {{ nodes.briefing.resumo }}", "dispositivo": "celular"},
        id="avisar",
    )
    wf.connect(report, notify)
    wf.add_trigger("agenda", report, {"cron": "0 7 * * *"})
    return wf


def foco_do_dia() -> Workflow:
    """08:30 on weekdays — ask the Decision Engine what to focus on, and say it.

    When there is no eligible goal, `decidir` emits nothing and the notification
    is skipped: silence instead of an empty message.
    """
    wf = Workflow(name="Foco do dia")
    decide = wf.add_node("decidir", {"pergunta": "proxima_meta"}, id="decidir")
    notify = wf.add_node(
        "notificar",
        {"texto": "Foco de hoje: {{ nodes.decidir.escolha }}. {{ nodes.decidir.justificativa }}"},
        id="avisar",
    )
    wf.connect(decide, notify)
    wf.add_trigger("agenda", decide, {"cron": "30 8 * * 1-5"})
    return wf


def guardiao_das_metas() -> Workflow:
    """09:00 — count open goals and speak up only when there are any."""
    wf = Workflow(name="Guardião das metas")
    goals = wf.add_node("meta_listar", {"status": "pending"}, id="metas")
    count = wf.add_node("agregar", {"operacao": "contar"}, id="contar")
    check = wf.add_node(
        "se",
        {"esquerda": "{{ nodes.contar.resultado }}", "operador": "maior", "direita": 0},
        id="tem_metas",
    )
    notify = wf.add_node(
        "notificar",
        {"texto": "Você tem {{ nodes.contar.resultado }} meta(s) em aberto."},
        id="avisar",
    )
    wf.connect(goals, count).connect(count, check)
    wf.connect(check, notify, source_port="true")
    wf.add_trigger("agenda", goals, {"cron": "0 9 * * *"})
    return wf


def sentinela_do_cerebro() -> Workflow:
    """Every 5 minutes — is Ollama answering? Record it, and warn once it isn't."""
    wf = Workflow(name="Sentinela do cérebro")
    health = wf.add_node("cerebro_saude", {}, id="saude")
    check = wf.add_node(
        "se", {"esquerda": "{{ nodes.saude.online }}", "operador": "verdadeiro"}, id="esta_online"
    )
    mark_online = wf.add_node(
        "mundo_definir",
        {"chave": "cerebro_local", "valor": "online", "categoria": "capabilities"},
        id="marcar_online",
    )
    mark_offline = wf.add_node(
        "mundo_definir",
        {"chave": "cerebro_local", "valor": "offline", "categoria": "capabilities"},
        id="marcar_offline",
    )
    warn = wf.add_node(
        "notificar",
        {"texto": "O cérebro local não está respondendo em {{ nodes.saude.endpoint }}."},
        id="avisar",
    )
    wf.connect(health, check)
    wf.connect(check, mark_online, source_port="true")
    wf.connect(check, mark_offline, source_port="false")
    wf.connect(mark_offline, warn)
    wf.add_trigger("intervalo", health, {"segundos": 300})
    return wf


def vigia_do_disco() -> Workflow:
    """Every 6 hours — warn when free disk space drops under 10 GB."""
    wf = Workflow(name="Vigia do disco")
    disk = wf.add_node("disco", {"caminho": ".", "alerta_livre_gb": 10.0}, id="disco")
    check = wf.add_node(
        "se", {"esquerda": "{{ nodes.disco.alerta }}", "operador": "verdadeiro"}, id="baixo"
    )
    notify = wf.add_node(
        "notificar",
        {"texto": (
            "Disco baixo: {{ nodes.disco.livre_gb }} GB livres "
            "({{ nodes.disco.usado_pct }}% usado)."
        )},
        id="avisar",
    )
    wf.connect(disk, check)
    wf.connect(check, notify, source_port="true")
    wf.add_trigger("agenda", disk, {"cron": "0 */6 * * *"})
    return wf


def backup_do_kernel() -> Workflow:
    """03:00 — snapshot the database, keep a week, announce it on the bus."""
    wf = Workflow(name="Backup do kernel")
    backup = wf.add_node(
        "backup_banco", {"destino": "backups", "manter": 7}, id="backup",
        policy={"max_attempts": 2, "backoff_seconds": 5, "timeout_seconds": 300},
    )
    announce = wf.add_node(
        "evento_publicar",
        {
            "tipo": "backup.concluido",
            "dados": {
                "arquivo": "{{ nodes.backup.arquivo }}",
                "bytes": "{{ nodes.backup.bytes }}",
            },
        },
        id="anunciar",
    )
    wf.connect(backup, announce)
    wf.add_trigger("agenda", backup, {"cron": "0 3 * * *"})
    return wf


def captura_rapida() -> Workflow:
    """A webhook inbox: POST a thought, it lands in memory and in today's file.

        curl -X POST http://127.0.0.1:8000/api/v1/automations/webhook/captura \\
             -H 'Content-Type: application/json' -d '{"texto":"ideia para o projeto"}'
    """
    wf = Workflow(name="Captura rápida")
    start = wf.add_node("inicio", {}, id="entrada")
    remember = wf.add_node(
        "memoria_gravar",
        {"conteudo": "{{ trigger.texto }}", "tipo": "note", "importancia": 0.6},
        id="gravar",
    )
    append = wf.add_node(
        "arquivo_escrever",
        {
            "caminho": "inbox/{{ now.date }}.md",
            "conteudo": "- {{ now.time }} — {{ trigger.texto }}\n",
            "modo": "acrescentar",
        },
        id="arquivar",
    )
    confirm = wf.add_node(
        "notificar", {"texto": "Anotado: {{ trigger.texto }}"}, id="confirmar"
    )
    wf.connect(start, remember).connect(start, append).connect(remember, confirm)
    wf.add_trigger("webhook", start, {"caminho": "captura"})
    return wf


def celebrar_meta() -> Workflow:
    """Reactive: whenever a goal is completed, remember it and say so."""
    wf = Workflow(name="Celebrar meta concluída")
    start = wf.add_node("inicio", {}, id="entrada")
    remember = wf.add_node(
        "memoria_gravar",
        {
            "conteudo": "Concluí a meta: {{ trigger.dados.title }}",
            "tipo": "fact",
            "importancia": 0.7,
        },
        id="gravar",
    )
    notify = wf.add_node(
        "notificar",
        {"texto": "Meta concluída: {{ trigger.dados.title }}. Bom trabalho."},
        id="avisar",
    )
    wf.connect(start, remember).connect(remember, notify)
    wf.add_trigger("evento", start, {"tipo": "objetivo.concluido"})
    return wf


def revisao_noturna() -> Workflow:
    """22:00 — the local model reviews the day and writes it to the journal.

    The `inicio` node keeps the review running on a quiet day: the world and goal
    lookups may come back empty, and the expressions fall back to `[]`.
    """
    wf = Workflow(name="Revisão noturna")
    start = wf.add_node("inicio", {}, id="entrada")
    world = wf.add_node("mundo_ler", {"tudo": True, "limite": 30}, id="mundo")
    goals = wf.add_node("meta_listar", {"status": "pending"}, id="metas")
    compose = wf.add_node(
        "texto",
        {
            "texto": (
                "Meu estado atual:\n{{ all.mundo || [] }}\n\n"
                "Minhas metas abertas:\n{{ all.metas || [] }}"
            ),
            "campo": "texto",
        },
        id="montar",
    )
    review = wf.add_node(
        "ia_resumir",
        {
            "texto": "{{ nodes.montar.texto }}",
            "instrucao": (
                "Faça uma revisão curta do meu dia em português: o que avançou, "
                "o que travou e a sugestão mais útil para amanhã."
            ),
            "max_palavras": 150,
        },
        id="revisar",
        policy={"timeout_seconds": 180},
    )
    journal = wf.add_node(
        "diario_escrever", {"conteudo": "{{ nodes.revisar.resumo }}"}, id="diario"
    )
    notify = wf.add_node(
        "notificar", {"texto": "Revisão do dia: {{ nodes.revisar.resumo }}"}, id="avisar"
    )
    wf.connect(start, world).connect(start, goals)
    wf.connect(start, compose).connect(world, compose).connect(goals, compose)
    wf.connect(compose, review).connect(review, journal).connect(review, notify)
    wf.add_trigger("agenda", start, {"cron": "0 22 * * *"})
    return wf


def revisao_semanal() -> Workflow:
    """Sunday 18:00 — a weekly briefing distilled into one durable memory."""
    wf = Workflow(name="Revisão semanal")
    report = wf.add_node("briefing", {"tipo": "daily"}, id="briefing")
    distil = wf.add_node(
        "ia_resumir",
        {
            "texto": "{{ nodes.briefing.resumo }}",
            "instrucao": (
                "Resuma a semana em português: os três pontos que mais importam "
                "e uma prioridade clara para a próxima."
            ),
            "max_palavras": 180,
        },
        id="destilar",
        policy={"timeout_seconds": 180},
    )
    remember = wf.add_node(
        "memoria_gravar",
        {
            "conteudo": "Revisão semanal ({{ now.date }}): {{ nodes.destilar.resumo }}",
            "titulo": "Revisão semanal {{ now.date }}",
            "tipo": "note",
            "importancia": 0.8,
        },
        id="gravar",
    )
    notify = wf.add_node(
        "notificar", {"texto": "Revisão semanal pronta: {{ nodes.destilar.resumo }}"},
        id="avisar",
    )
    wf.connect(report, distil).connect(distil, remember).connect(distil, notify)
    wf.add_trigger("agenda", report, {"cron": "0 18 * * 0"})
    return wf


# ---------------------------------------------------------------- the catalog

CATALOG: list[tuple[str, callable, str, list[str], bool]] = [
    (
        "briefing-matinal", briefing_matinal,
        "Todo dia às 07:00, gera o briefing e te avisa.",
        ["diario", "briefing"], False,
    ),
    (
        "foco-do-dia", foco_do_dia,
        "Dias úteis às 08:30, decide seu foco e avisa (silencia se não houver meta).",
        ["diario", "metas"], False,
    ),
    (
        "guardiao-das-metas", guardiao_das_metas,
        "Todo dia às 09:00, avisa quantas metas estão abertas.",
        ["metas"], False,
    ),
    (
        "sentinela-do-cerebro", sentinela_do_cerebro,
        "A cada 5 minutos, verifica o cérebro local e registra o estado no World Model.",
        ["sistema", "saude"], True,
    ),
    (
        "vigia-do-disco", vigia_do_disco,
        "A cada 6 horas, avisa se o disco estiver abaixo de 10 GB livres.",
        ["sistema", "saude"], True,
    ),
    (
        "backup-do-kernel", backup_do_kernel,
        "Todo dia às 03:00, faz backup consistente do banco e mantém 7 cópias.",
        ["sistema", "backup"], True,
    ),
    (
        "captura-rapida", captura_rapida,
        "Webhook /automations/webhook/captura: guarda a ideia na memória e no inbox do dia.",
        ["captura", "webhook"], True,
    ),
    (
        "celebrar-meta", celebrar_meta,
        "Quando uma meta é concluída, registra na memória e te avisa.",
        ["metas", "evento"], True,
    ),
    (
        "revisao-noturna", revisao_noturna,
        "Às 22:00, o cérebro local revisa seu dia e escreve no diário.",
        ["diario", "ia"], False,
    ),
    (
        "revisao-semanal", revisao_semanal,
        "Domingo às 18:00, destila a semana em uma memória duradoura.",
        ["semanal", "ia"], False,
    ),
]


def build_all() -> list[tuple[str, Workflow, str, list[str], bool]]:
    """Every catalog workflow, built. Useful for tests and for `teia catalogo`."""
    return [
        (slug, builder(), description, tags, enabled)
        for slug, builder, description, tags, enabled in CATALOG
    ]


def seed(service, db: Session, owner_id: str, *, overwrite: bool = False) -> list[str]:
    """Install the catalog for an owner. Existing automations are left alone.

    Re-seeding never clobbers the owner's edits: a slug that already exists is
    skipped unless `overwrite` is explicitly asked for.
    """
    installed: list[str] = []
    for slug, builder, description, tags, enabled in CATALOG:
        if not overwrite and service.store.get(db, owner_id, slug):
            continue
        try:
            service.save(
                db, owner_id, builder(), slug=slug, description=description,
                enabled=enabled, tags=tags, source="catalog",
            )
            installed.append(slug)
        except Exception as e:  # noqa: BLE001 — one bad recipe must not block the rest
            logger.warning("catálogo: '%s' não pôde ser instalada: %s", slug, e)
    if installed:
        logger.info("Teia: %d automação(ões) do catálogo instaladas", len(installed))
    return installed
