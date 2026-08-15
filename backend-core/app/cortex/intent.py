"""
Intent — a unidade de entendimento do cortex.

Uma intenção é o resultado de casar a fala contra a gramática declarativa do
cortex: `verb` (o que fazer), `target` (sobre o quê), `params` (detalhes
extraídos), e `trace` (quais padrões casaram — a trilha de auditoria).

O parser é determinístico: nenhuma estatística, nenhum chute. Ou a frase
casa com um padrão e a intenção nasce com trace, ou devolve None e o cortex
diz honestamente que não entendeu — e lista os verbos que conhece.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Intent:
    verb: str
    target: str | None
    params: dict = field(default_factory=dict)
    raw: str = ""
    trace: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "verb": self.verb,
            "target": self.target,
            "params": self.params,
            "raw": self.raw,
            "trace": self.trace,
        }


class VerbSpec:
    """Um verbo do cortex: nome + padrões de fala + descrição (para o 'não
    entendi' honesto listar o que o dono pode pedir)."""

    def __init__(self, name: str, description: str, patterns: list[re.Pattern]):
        self.name = name
        self.description = description
        self.patterns = patterns


def match_verb(verb: VerbSpec, text: str) -> tuple[str, dict, list[str]] | None:
    """Tenta casar `text` contra os padrões do verbo. Devolve
    (target, params, trace) no primeiro padrão que casa inteiro, ou None."""
    for i, pat in enumerate(verb.patterns):
        m = pat.fullmatch(text)
        if not m:
            continue
        params = {k: v for k, v in m.groupdict().items() if v is not None}
        target = params.pop("target", None)
        return target, params, [f"{verb.name}:padrão{i + 1} ({pat.pattern[:40]}…)"]
    return None


def parse(verb_specs: list[VerbSpec], text: str) -> Intent | None:
    """Casa `text` contra todos os verbos, na ordem do registro. Primeiro
    verbo que casar ganha — a ordem é a própria prioridade declarada."""
    cleaned = re.sub(r"\s+", " ", text or "").strip().strip(".,!?")
    if not cleaned:
        return None
    for verb in verb_specs:
        hit = match_verb(verb, cleaned)
        if hit is None:
            continue
        target, params, trace = hit
        return Intent(verb=verb.name, target=target, params=params, raw=cleaned, trace=trace)
    return None
