# Sexta-Feira — Visão do Projeto

> O Sexta-Feira é um **Sistema Operacional de Inteligência Pessoal** — um JARVIS real,
> exclusivo do seu dono. Não é um chatbot: ele **lembra, aprende, entende contexto,
> antecipa, e AGE** em vários dispositivos, sempre local, privado e sob controle do dono.

Este documento é a **estrela-guia** do projeto. Cada capacidade abaixo é marcada com o
estado real, sem inflar: ✅ pronto · 🔧 parcial · 📋 planejado — e o que tecnicamente exige.

---

## Princípios (inegociáveis)

- **Exclusivo do dono.** Memória, histórico, preferências e conhecimento pertencem só a ele.
- **Local e privado.** Roda na máquina do dono (Ollama). Sem nuvem de IA. Sem telemetria.
- **Ele age, não só responde.** Decide e executa ações reais quando autorizado.
- **Cresce com o uso.** Quanto mais convive, mais entende e mais útil fica.
- **Um cérebro, muitos corpos.** Celular, computador, carro, wearables — mesma mente.
- **Fala natural, explica o raciocínio quando pedido.**

---

## Arquitetura em uma frase

**O CÉREBRO decide (pronto). As MÃOS executam em cada corpo (o próximo grande salto).**

```
  Você fala no celular
        │ voz/chat (rede privada / túnel)
        ▼
  CÉREBRO (máquina sempre-ligada): Ollama + memória-grafo + tool-calling
        │ decide a ação
        ├──► Teia (automações em Python, dentro do kernel)       ✅ ponte pronta
        ├──► Agente do CELULAR (intents Android: ligar, apps…)  ✅ v1 construída
        └──► Agente do COMPUTADOR (abrir apps, scripts, arquivos) 📋 a construir
```

O ponto-chave: o cérebro **já decide e dispara** (tool-calling + n8n). Para "abrir o
WhatsApp" ou "abrir o Android Studio", falta o **executor rodando em cada corpo** —
um app/daemon que recebe a ordem do cérebro e executa nativamente.

---

## Capacidades × estado real

### 🧠 Memória contínua (segundo cérebro) — ✅ construído
Memória de longo prazo como **grafo de conhecimento** (pessoas, projetos, ideias,
compromissos, preferências, decisões, soluções que funcionaram/erros). Ligações
automáticas (semânticas + `[[wikilinks]]`) **nomeadas** ("trabalha em"), e recall em
rede que conecta o antigo ao novo. Persiste local, cresce com o tempo, sob controle do dono.
*Falta:* decaimento/importância avançada, linha do tempo ("há 3 meses você disse…").

### 📚 Aprendizado contínuo — 🔧 parcial
Auto-aprende fatos após cada conversa (✅). Pipeline de **fine-tuning (LoRA)** para
absorver o seu jeito de falar/escrever está pronto e documentado, mas **ainda não rodado**.
*Falta:* rodar o treino nos seus dados; aprender rotina/horários/locais como sinais.

### 🤖 Execução de ações — 🔧 parcial (cérebro + transporte prontos; falta o executor no corpo)
Tool-calling agêntico (✅): de uma frase, o cérebro escolhe e dispara `remember`,
`recall`, `run_automation` (n8n) e `device_action`. O **Protocolo de Ação** (✅) já leva
`{action, params}` ao corpo alvo (fila persistida + WebSocket ao vivo + resultado). *Falta:*
o **agente nativo em cada corpo** (Android/Desktop) que de fato executa a ação recebida.

### 📱 Controle do celular (ligar, apps, câmera, notificações) — 🔧 parcial
O **Agente Android** existe (✅ v1): serviço em foreground que ouve o canal de ações
(`/api/v1/actions/stream`, WebSocket com fallback por polling) e executa nativamente — abrir
apps, navegar (geo/maps), discar (ACTION_DIAL), compor SMS e mostrar notificações — sempre
com o dono mantendo o toque final (nada é feito sem a última confirmação na tela). Resultados
voltam ao kernel. *Falta:* ler/resumir notificações, câmera, mídia e acessibilidade.

### 🧭 Navegação / 📞 Telefonia / 💬 Mensagens — 📋 planejado
Casos do Agente Android (Waze/Maps por intent, chamadas, SMS, ler/resumir/responder).
Alguns fluxos (enviar mensagem via API) podem sair por **n8n** já hoje.

### 💻 Controle do computador (apps, scripts, arquivos, backup) — 📋 planejado
Exige um **Agente de Desktop** (daemon local): abre programas, roda scripts, move
arquivos, monitora recursos — recebendo ordens do cérebro.

### 👨‍💻 Parceiro de desenvolvimento — 🔧 parcial
Conversar sobre código, explicar erros/algoritmos: funciona hoje (chat). Executar
(build, testes, commit, abrir projeto) depende do **Agente de Desktop** + tools de dev.

### 🔐 Cibersegurança (estudo autorizado) · 🎓 Estudos · ✅ Produtividade — 🔧 parcial
Orientação/explicação/planejamento funcionam por conversa hoje. **Lembretes e ações
agendadas no tempo** já funcionam (✅ agendador: "me lembra disso daqui a 2 meses" →
dispara sozinho na hora). Flashcards, montar lab, cronogramas viram **tools/automações**.
*Escopo:* só ambientes próprios e autorizados.

### 🌐 Internet / APIs ("executar tudo") — 🔧 base pronta
**Sistema de conectores** (✅): o dono cadastra capacidades de API e o cérebro as
executa por nome; chaves criptografadas (cofre Fernet), sem URL arbitrária. Escala p/
milhares de APIs. *Falta:* catálogo grande semeado + busca na web como capacidade padrão.

### ❤️ Saúde & wearables · 🏠 Casa inteligente — 📋 planejado
Wearables e casa entram via **conectores/n8n**. Saúde: sugere hábitos e quando procurar
profissional; **nunca** diagnostica.

### 🧑‍🤝‍🧑 Sub-agentes (Jarvis cria auxiliares) — 🔧 base pronta
O cérebro **delega** sub-tarefas a sub-agentes locais especializados (✅), com toolset
restrito (consultam, não agem no mundo) e sem recursão — local e owner-scoped. *Falta:*
sub-agentes persistentes/nomeados e um "conselho" que delibera.

### 🎭 Personalidade — ✅ configurável
Persona (leal, natural, proativa, discreta) definida em config; lembra do contexto.

### 🔭 Evolução futura (multi-dispositivo) — 🔧 base pronta
Modelo de "corpos" (device pairing) existe; a experiência contínua entre celular,
PC, carro, relógio e óculos depende dos **executores por dispositivo** + sync privado.

---

## O que já está pronto e verificado (na `main`, com CI verde)

1. Kernel privado local, dono único, multi-dispositivo (pareamento).
2. Memória-grafo persistente (estilo Obsidian) com relações nomeadas.
3. Voz local offline (STT faster-whisper + TTS Piper).
4. Automações via **n8n** self-hosted (a ponte para agir).
5. **Tool-calling agêntico**: o cérebro decide e executa sozinho, por voz, do celular.
6. Fundação de produção: CI, migrações (Alembic), lint, testes.

## O próximo grande salto: **Protocolo de Ação por dispositivo**

Para cumprir "abra o WhatsApp / ligue pro meu pai / abra o Android Studio / rode os
testes", o cérebro precisa **entregar ordens aos corpos**. O plano:

1. **Protocolo de Ação** no kernel: fila/stream de comandos por dispositivo + resultados. ✅
2. **Agente Android**: recebe e executa ações nativas (o celular vira "mãos"). ✅ v1
3. **Agente de Desktop**: idem para o computador. 📋
4. Tools do cérebro (`device_action`) que despacham para o corpo certo. ✅

O kernel (contrato + fila + tools) é construível e **verificável com CI aqui**; os
agentes nativos (Android/Desktop) você valida nos respectivos ambientes.

---

*Construído com intenção. Usado com propósito. Exclusivo do seu dono.*
