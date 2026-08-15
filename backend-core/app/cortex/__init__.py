"""
Cortex — o segundo cérebro, construído à mão. Sem LLM, sem Ollama, sem
modelo local: intenções por gramática determinística, decisões por regras
declarativas, respostas por persona. O modelo de linguagem, se um dia
existir aqui, será um periférico — nunca o cérebro.

Ciclo da fala (sem LLM no caminho):
  fala -> STT (periférico: só ouvir) -> cortex.parse() -> verbo+alvo+params
       -> handler executa (engines reais) -> respond() com a persona do pack
       -> TTS (periférico: só falar)

Nada aqui decide por estatística: ou a gramática reconheceu a intenção e o
trace mostra por quê, ou o cortex diz que não entendeu e lista o que sabe
fazer — nunca chuta.
"""
from app.cortex.intent import Intent, parse
from app.cortex.run import run_intent
from app.cortex.verbs import VERBS, known_verbs

__all__ = ["Intent", "parse", "run_intent", "VERBS", "known_verbs"]
