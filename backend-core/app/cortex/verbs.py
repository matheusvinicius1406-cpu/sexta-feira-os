"""
Verbos do cortex — a gramática declarativa de fala em pt-BR.

Cada verbo é uma lista de padrões (regex com grupos nomeados). A ordem dos
verbos no registro é a prioridade: `tocar playlist X` precisa casar antes do
genérico `tocar X`. Os padrões aceitam as formas naturais de fala; o resolver
(função em run.py) executa a ação real nas engines — nada de estatística.
"""
from __future__ import annotations

import re

from app.cortex.intent import VerbSpec

_H = re.I  # shorthand: case-insensitive

# Grupo de abertura comum: formas naturais de pedir uma ação.
_OPEN = r"(?:toca|toque|tocar|coloca|colocar|bota|botar|p[oõ]e|pode tocar|pode colocar)\s+"
_OPEN_ART = r"(?:a\s+|o\s+)?"

VERBS: list[VerbSpec] = [
    # ── Música / rádio ─────────────────────────────────────
    VerbSpec(
        "tocar_playlist",
        "tocar a playlist <nome> (ex.: 'tocar a playlist treino')",
        [
            re.compile(rf"^{_OPEN}{_OPEN_ART}playlist\s+(?P<target>.+?)\s*$", _H),
            re.compile(rf"^(?:inicia|iniciar|liga|ligar)\s+{_OPEN_ART}playlist\s+(?P<target>.+?)\s*$", _H),
        ],
    ),
    VerbSpec(
        "tocar_preset",
        "tocar o preset <número> (ex.: 'tocar o preset 3')",
        [
            re.compile(rf"^{_OPEN}{_OPEN_ART}(?:preset|esta[çc][ãa]o)\s+(?P<target>\d{{1,2}})\s*$", _H),
            re.compile(r"^(?:preset|esta[çc][ãa]o)\s+(?P<target>\d{1,2})\s*$", _H),
        ],
    ),
    VerbSpec(
        "tocar",
        "tocar <música ou estação> (ex.: 'tocar rock clássico')",
        [
            re.compile(rf"^{_OPEN}{_OPEN_ART}(?P<target>.+?)\s*$", _H),
        ],
    ),
    VerbSpec(
        "colar",
        "colar um link de música (ex.: 'colar https://youtu.be/…')",
        [
            re.compile(r"^(?:colar|coloca|cola)\s+(?P<target>https?://\S+)\s*$", _H),
        ],
    ),
    VerbSpec(
        "volume",
        "definir o volume (ex.: 'volume 50', 'aumenta o volume')",
        [
            re.compile(r"^volume\s+(?P<target>\d{1,3})\s*$", _H),
            re.compile(r"^(?:aumenta|aumentar|sobe|subir)\s+o?\s*(?:volume|som)\s*$", _H),
            re.compile(r"^(?:diminui|diminuir|abaixa|abaixar)\s+o?\s*(?:volume|som)\s*$", _H),
        ],
    ),
    VerbSpec(
        "pular",
        "pular a faixa (ex.: 'pular', 'próxima música')",
        [
            re.compile(r"^(?:pular|pula|pule|pr[oó]xima|avan[çc]a|avan[çc]ar)\s*(?:a\s+|a\s+m[úu]sica|m[úu]sica|faixa)?\s*$", _H),
        ],
    ),
    VerbSpec(
        "parar",
        "parar a música (ex.: 'para a música', 'silêncio')",
        [
            re.compile(r"^(?:para|parar|pausa|pausar|sil[eê]ncia|cala|calar)\s*(?:a\s+m[úu]sica|m[úu]sica|o\s+som|som)?\s*$", _H),
        ],
    ),
    VerbSpec(
        "salvar_playlist",
        "salvar a fila como playlist (ex.: 'salvar playlist treino')",
        [
            re.compile(r"^(?:salvar|salva|guarda)\s+playlist\s+(?P<target>.+?)\s*$", _H),
        ],
    ),
    VerbSpec(
        "modo",
        "alternar modos do rádio (ex.: 'embaralhar', 'repetir', 'adblock ligar')",
        [
            re.compile(r"^(?P<target>embaralhar|n[ãa]o\s+embaralhar)\s*$", _H),
            re.compile(r"^(?P<target>repetir|n[ãa]o\s+repetir)\s*$", _H),
            re.compile(r"^adblock\s+(?P<target>ligar|desligar)\s*$", _H),
        ],
    ),
    # ── Voz / persona ──────────────────────────────────────
    VerbSpec(
        "voz",
        "trocar a voz (ex.: 'usar voz ultron', 'fala como o alfred')",
        [
            re.compile(r"^(?:usar|trocar|troca|ativa|ativar|muda|mudar)\s+(?:a\s+|pra\s+|para\s+|de\s+voz\s+para\s+)?voz\s+(?P<target>\w+)\s*$", _H),
            re.compile(r"^(?:fala|fale|responda|responde)\s+como\s+(?:o\s+|a\s+)?(?P<target>\w+)\s*$", _H),
            re.compile(r"^voz\s+(?P<target>\w+)\s*$", _H),
        ],
    ),
    VerbSpec(
        "falar",
        "o Jarvis fala um texto (ex.: 'fala bom dia')",
        [
            re.compile(r"^(?:fala|fale|falar|diga|diz|repita|repetir)\s+(?P<target>.+?)\s*$", _H),
        ],
    ),
    # ── Memória ────────────────────────────────────────────
    VerbSpec(
        "guardar",
        "guardar na memória (ex.: 'guarda que hoje tenho reunião às 9')",
        [
            re.compile(r"^(?:guarda|guardar|lembra|lembre-se|memoriza|memorize|anota|anotar)\s+(?:que\s+|disto\s+|disso\s+|isto\s+|isso\s+)?(?P<target>.+?)\s*$", _H),
        ],
    ),
    VerbSpec(
        "esquecer",
        "esquecer da memória (ex.: 'esquece que tenho reunião às 9')",
        [
            re.compile(r"^(?:esquece|esquecer|apaga|apagar)\s+(?:que\s+|da\s+mem[óo]ria\s+)?(?P<target>.+?)\s*$", _H),
        ],
    ),
    # ── Metas ──────────────────────────────────────────────
    VerbSpec(
        "criar_meta",
        "criar uma meta (ex.: 'criar meta ler 20 páginas por dia')",
        [
            re.compile(r"^(?:criar|cria|adicionar|adiciona)\s+(?:uma\s+|a\s+)?meta\s+(?P<target>.+?)\s*$", _H),
        ],
    ),
    VerbSpec(
        "concluir_meta",
        "concluir uma meta (ex.: 'concluir meta ler 20 páginas')",
        [
            re.compile(r"^(?:concluir|conclui|completar|completa|finalizar|finaliza)\s+(?:a\s+)?meta\s+(?P<target>.+?)\s*$", _H),
        ],
    ),
    # ── Informação ─────────────────────────────────────────
    VerbSpec(
        "hora",
        "saber as horas (ex.: 'que horas são')",
        [
            re.compile(r"^(?:que\s+horas\s+s[ãa]o|hora|horas?|que\s+hora\s+[ée])\s*\??$", _H),
        ],
    ),
    VerbSpec(
        "status",
        "saber o estado do sistema (ex.: 'como está o sistema', 'status')",
        [
            re.compile(r"^(?:como\s+est[áa]\s+(?:o\s+)?(?:sistema|o\s+jarvis|voc[eê])|status|estado\s+do\s+sistema)\s*\??$", _H),
        ],
    ),
]

# Ordem de teste: os verbos mais específicos vêm primeiro (playlist/preset
# antes do tocar genérico) — a lista acima já está nessa ordem.
_ORDER = {v.name: i for i, v in enumerate(VERBS)}


def known_verbs() -> list[str]:
    """Nomes na ordem de prioridade — para o 'não entendi' honesto."""
    return [v.name for v in VERBS]
