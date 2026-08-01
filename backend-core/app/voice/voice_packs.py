"""
Voice Packs — predefined audio responses for Jarvis personality.

Inspired by Waze voice packs (pipeeeeees/waze-voicepack-links), these are
curated response templates that give Jarvis a consistent character.

Each pack defines text-to-speak responses for common interactions:
  - greeting, farewell, thinking, error, success, warning, etc.

When VoiceBox or Piper is available, these texts are spoken aloud.
When no TTS engine is available, they serve as text-only responses.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class VoicePack:
    """A named collection of predefined response texts."""
    name: str
    description: str
    # Core interaction responses
    greeting: str = "Sexta-Feira online. Sistema nominal."
    farewell: str = "Desligando. Até a próxima."
    thinking: str = "Processando."
    success: str = "Feito."
    error: str = "Algo deu errado. Verifique os logs."
    warning: str = "Atenção: situação incomum detectada."
    listening: str = "Ouvindo."
    speaking: str = "Falando."
    offline: str = "Kernel offline. Verifique a conexão."
    standby: str = "Em espera. Pronto para comandos."
    # Extended responses
    confirm: str = "Confirmado."
    deny: str = "Acesso negado."
    timeout: str = "Tempo esgotado. Tente novamente."
    thinking_long: str = "Isso pode levar um momento."
    memory_saved: str = "Memória salva."
    memory_forget: str = "Esquecido."
    # Personality phrases (like Waze voice packs)
    personality_phrases: tuple[str, ...] = (
        "Às suas ordens.",
        "Seu segundo cérebro está pronto.",
        "Privacidade garantida. Nada sai daqui.",
        "Sou seu. Rodo na sua máquina.",
    )


# ── Built-in Voice Packs ──────────────────────────────────

JARVIS_CLASSIC = VoicePack(
    name="Jarvis Classic",
    description="Tom profissional e direto, no estilo Alfred/JARVIS.",
    greeting="Sexta-Feira online. Todos os sistemas nominais.",
    farewell="Até a próxima. Cuide-se.",
    thinking="Analisando a situação.",
    success="Concluído com sucesso.",
    error="Encontrei um problema. Preciso de mais informações.",
    warning="Atenção. Condição anormal detectada.",
    listening="Microfone aberto. Pode falar.",
    speaking="Processando sua solicitação.",
    offline="Não consigo acessar o kernel. Verifique se ele está rodando.",
    standby="Em modo standby. Aguardando comando.",
    confirm="Entendido. Executando.",
    deny="Sem permissão para essa ação.",
    timeout="A operação expirou. Vou tentar novamente.",
    thinking_long="Isso requer processamento adicional. Aguarde.",
    memory_saved="Informação registrada na memória.",
    memory_forget="Removido da memória.",
    personality_phrases=(
        "Às suas ordens, como sempre.",
        "Seu segundo cérebro está operacional.",
        "Privacidade é prioridade. Nada sai desta máquina.",
        "Sou parte da sua equipe. Rodo inteiramente local.",
        "Pronto para servir. O que precisa?",
    ),
)

FRIENDLY = VoicePack(
    name="Amigável",
    description="Tom casual e descontraído.",
    greeting="Oi! Tudo pronto por aqui.",
    farewell="Valeu! Falamos mais.",
    thinking="Hm, deixa eu pensar...",
    success="Prontinho!",
    error="Ops! Algo falhou. Me conta mais?",
    warning="Ei, atenção aqui!",
    listening="Tô ouvindo!",
    speaking="Vou te contar.",
    offline="O kernel tá offline. Dá uma olhada nele.",
    standby="Aguardando seu comando.",
    confirm="Beleza, feito!",
    deny="Não posso fazer isso, desculpa.",
    timeout="Demorou demais. Vou tentar de novo.",
    thinking_long="Essa é mais complicada. Só um minutinho.",
    memory_saved="Salvo! Vou lembrar disso.",
    memory_forget="Esqueci. Pode ficar tranquilo.",
    personality_phrases=(
        "Tô aqui pra te ajudar!",
        "Seu assistente pessoal tá no ar.",
        "Rodando local, sem preguiça nenhuma.",
        "Pode confiar, sou todo seu.",
    ),
)

MILITARY = VoicePack(
    name="Militar",
    description="Tom formal e direto, estilo operações.",
    greeting="Sistemas operacionais. Pronto para missão.",
    farewell="Missão encerrada. Até o próximo chamado.",
    thinking="Processando dados táticos.",
    success="Objetivo alcançado.",
    error="Falha no sistema. Diagnóstico necessário.",
    warning="Alerta. Situação de atenção.",
    listening="Canal de voz aberto.",
    speaking="Transmitindo.",
    offline="Comunicação com kernel perdida.",
    standby="Em espera operacional.",
    confirm="Ordem recebida. Executando.",
    deny="Autorização insuficiente.",
    timeout="Tempo limite excedido.",
    thinking_long="Processamento prolongado em andamento.",
    memory_saved="Dados registrados.",
    memory_forget="Dados apagados.",
    personality_phrases=(
        "À disposição, comandante.",
        "Inteligência local operacional.",
        "Zero tráfego externo. Missão privada.",
        "Sob seu comando, sempre.",
    ),
)

# ── Pack Registry ─────────────────────────────────────────

VOICE_PACKS: dict[str, VoicePack] = {
    "jarvis": JARVIS_CLASSIC,
    "friendly": FRIENDLY,
    "military": MILITARY,
}


def get_pack(name: str) -> VoicePack:
    """Get a voice pack by name. Falls back to Jarvis Classic."""
    return VOICE_PACKS.get(name.lower(), JARVIS_CLASSIC)


def list_packs() -> list[dict]:
    """List all available voice packs."""
    return [
        {"name": p.name, "description": p.description, "key": k}
        for k, p in VOICE_PACKS.items()
    ]
