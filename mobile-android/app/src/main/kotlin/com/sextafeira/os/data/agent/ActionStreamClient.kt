package com.sextafeira.os.data.agent

import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import timber.log.Timber
import java.util.concurrent.TimeUnit

/**
 * The live channel to the kernel's Action Protocol.
 *
 * Primary path: a WebSocket to /api/v1/actions/stream?token=<device>, which the
 * kernel uses to push commands in real time (and replays the backlog on
 * connect). While the socket is down it falls back to polling
 * /api/v1/actions/pending and reporting results over REST — the same protocol,
 * the same device token, so a blocked WS degrades to "slower, but still hands".
 */
class ActionStreamClient(
    private val executor: ActionExecutor,
    private val baseUrlProvider: suspend () -> String,
    private val deviceTokenProvider: suspend () -> String?,
) {

    private val gson = Gson()
    private val client = OkHttpClient.Builder()
        .pingInterval(20, TimeUnit.SECONDS)      // keep the socket alive through NATs
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(0, TimeUnit.MILLISECONDS)   // WebSocket: no read deadline
        .build()

    @Volatile
    private var connected = false
    private var stopped = false
    private var scope: CoroutineScope? = null
    private var ws: WebSocket? = null
    private var pollingJob: Job? = null

    /** Start listening. Runs until [stop] — safe to call once. */
    fun start(scope: CoroutineScope, onStatus: (AgentStatus) -> Unit) {
        if (this.scope != null) return // already running
        this.scope = scope
        stopped = false

        scope.launch {
            var backoffMs = 2_000L
            while (scope.isActive && !stopped) {
                val token = deviceTokenProvider()
                if (token.isNullOrBlank()) {
                    onStatus(AgentStatus.Unpaired)
                    delay(10_000)
                    continue
                }

                val base = baseUrlProvider().trimEnd('/')
                val wsUrl = base.replaceFirst("http", "ws") +
                    "/api/v1/actions/stream?token=" + token

                connected = false
                val socket = client.newWebSocket(
                    Request.Builder().url(wsUrl).build(),
                    listener(onStatus),
                )
                ws = socket

                // Wait until the socket drops (or we are stopped), then reconnect.
                while (connected && !stopped && scope.isActive) {
                    delay(1_000)
                }
                socket.close(1_000, "reconectando")
                if (stopped) break
                onStatus(AgentStatus.Reconnecting)
                delay(backoffMs)
                backoffMs = (backoffMs * 2).coerceAtMost(60_000)
            }
        }

        // Polling fallback: only acts while the socket is not delivering.
        pollingJob = scope.launch {
            while (scope.isActive && !stopped) {
                if (!connected) pollPending(onStatus)
                delay(15_000)
            }
        }
    }

    fun stop() {
        stopped = true
        ws?.close(1_000, "agente desligado")
        ws = null
        pollingJob?.cancel()
        pollingJob = null
        scope = null
    }

    // ── WebSocket ──────────────────────────────────────────

    private fun listener(onStatus: (AgentStatus) -> Unit) = object : WebSocketListener() {
        override fun onOpen(webSocket: WebSocket, response: Response) {
            connected = true
            onStatus(AgentStatus.Connected)
        }

        override fun onMessage(webSocket: WebSocket, text: String) {
            handleCommand(text, onStatus)
        }

        override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
            Timber.d(t, "socket de ações caiu")
            connected = false
            onStatus(AgentStatus.Disconnected)
        }

        override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
            connected = false
            onStatus(AgentStatus.Disconnected)
        }
    }

    private fun handleCommand(text: String, onStatus: (AgentStatus) -> Unit) {
        if (!text.contains("\"command\"")) return // hello/ack/others are ignored
        try {
            val msg = gson.fromJson(text, DeviceCommand::class.java)
            if (msg.id.isBlank()) return
            scope?.launch {
                val outcome = executor.execute(msg.action, msg.params ?: emptyMap())
                sendResult(msg.id, outcome)
                onStatus(AgentStatus.ActionDone(msg.action))
            }
        } catch (e: Exception) {
            Timber.w(e, "comando inválido: %s", text)
        }
    }

    private fun sendResult(commandId: String, outcome: ActionResult) {
        val payload = gson.toJson(
            DeviceResult(
                id = commandId,
                status = outcome.status,
                result = outcome.result,
                error = outcome.error,
            )
        )
        ws?.send(payload)
    }

    // ── Polling fallback ───────────────────────────────────

    private suspend fun pollPending(onStatus: (AgentStatus) -> Unit) {
        val token = deviceTokenProvider() ?: return
        val base = baseUrlProvider().trimEnd('/')
        try {
            val resp = client.newCall(
                Request.Builder()
                    .url("$base/api/v1/actions/pending")
                    .header("Authorization", "Bearer $token")
                    .build()
            ).execute()
            resp.use {
                if (!it.isSuccessful) return
                val body = it.body?.string() ?: return
                val type = object : TypeToken<List<DeviceCommand>>() {}.type
                val commands: List<DeviceCommand> = gson.fromJson(body, type) ?: return
                for (cmd in commands) {
                    if (cmd.id.isBlank()) continue
                    val outcome = executor.execute(cmd.action, cmd.params ?: emptyMap())
                    reportRest(base, token, cmd.id, outcome)
                    onStatus(AgentStatus.ActionDone(cmd.action))
                }
            }
        } catch (e: Exception) {
            Timber.d("polling de ações indisponível: %s", e.message)
        }
    }

    private fun reportRest(base: String, token: String, commandId: String, outcome: ActionResult) {
        val payload = gson.toJson(
            DeviceResult(
                id = commandId,
                status = outcome.status,
                result = outcome.result,
                error = outcome.error,
            )
        )
        client.newCall(
            Request.Builder()
                .url("$base/api/v1/actions/$commandId/result")
                .header("Authorization", "Bearer $token")
                .post(payload.toRequestBody("application/json".toMediaType()))
                .build()
        ).execute().close()
    }
}
