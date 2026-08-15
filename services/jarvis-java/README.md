# jarvis-java — o worker JVM do Sexta-Feira OS

O kernel é Python e é a fonte da verdade. Este serviço Java existe para o que
a JVM faz melhor que Python: **processamento de bytes em paralelo** (áudio,
streaming) com zero GIL e latência baixa. Ele **nunca inventa estado** — só
processa o que recebe e reporta o que mediu, falando com o kernel pela API
dele.

## Endpoints

| Rota | O que faz |
|---|---|
| `GET /health` | Status do serviço + **ping ao vivo ao kernel Python** (o elo Java↔Python, provado a cada request) |
| `POST /api/v1/audio/waveform` | `{"url": "...", "max_seconds": 60}` — baixa um áudio (cap 40 MB), decodifica para WAV (ffmpeg) e devolve **picos RMS por segundo** em 0..1 — pronto para o HUD renderizar a forma de onda da faixa tocando |

## Como rodar

```bash
cd services/jarvis-java
./gradlew run            # primeiro: baixa o Gradle + dependências
# env: JARVIS_JAVA_PORT=17494 (padrão), KERNEL_URL=http://127.0.0.1:8000 (padrão)
```

Testes:

```bash
./gradlew test
```

## O elo com o kernel

```bash
curl http://127.0.0.1:17494/health
# {"service":"jarvis-java","kernel":{"ok":true,"latency_ms":3,"url":"http://127.0.0.1:8000"},...}

curl -X POST http://127.0.0.1:17494/api/v1/audio/waveform \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/musica.mp3","max_seconds":30}'
# {"peaks":[0.12,0.45,...],"duration_s":30,"source":"...","bytes":...}
```

O HUD pode apontar para este serviço (via proxy do vite) para visualizar a
faixa; o kernel continua dono da fila e do estado.
