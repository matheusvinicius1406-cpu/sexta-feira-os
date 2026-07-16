# Contexto do Projeto

## Missão

Construir o **Sexta-Feira** como um *segundo cérebro* pessoal: um kernel cognitivo
que roda **inteiramente na máquina do dono**, aprende com ele e serve só a ele —
no espírito de um Alfred / JARVIS. Íntimo, privado, absoluto.

## Princípios (inegociáveis)

- **Local-only.** Todo raciocínio e embedding rodam via Ollama, na máquina do dono. Nenhum LLM externo, nenhuma nuvem, nenhum dado sai do host.
- **Dono único.** Uma só conta. Sem cadastro aberto. Dispositivos são pareados explicitamente.
- **Multilocal — um cérebro, vários corpos.** Celular, carro, óculos, relógio, desktop conectam ao mesmo cérebro pela rede privada do dono.
- **Memória de verdade.** Fatos, preferências e histórico persistem localmente (SQLite + embeddings locais) e sobrevivem a reinícios.
- **Ele aprende.** A história do dono vira dataset para fine-tuning (LoRA); o modelo fica cada vez mais *dele*.
- **Privacidade por construção.** Sem telemetria. Sem rastreamento. Acesso remoto só por túnel privado (Tailscale/WireGuard), nunca internet pública.

## O que NÃO é

- Não é SaaS. Não é multiusuário. Não conversa com OpenAI/Claude/Gemini.
- Não pretende treinar um modelo de fronteira (500B+) do zero — isso custa dezenas
  de milhões e exigiria data-center, quebrando a privacidade. O caminho é **partir de
  um modelo aberto local e especializá-lo nos dados do dono**.

## Objetivos de longo prazo

1. Um cérebro local que anticipa, lembra e executa — sempre sob controle do dono.
2. Presença ambiente: mesmo cérebro acessível do celular ao carro aos óculos.
3. Aprendizado contínuo: memória agora, fine-tuning periódico depois.
4. Camada de percepção de baixa latência (o runtime Rust em `src/`, futuro) para os corpos ambientes.
