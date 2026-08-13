package com.sextafeira.os.data.agent

import kotlinx.coroutines.flow.MutableStateFlow

/** Shared, observable state of the agent service, for the Settings UI. */
object AgentMonitor {
    val status: MutableStateFlow<AgentStatus?> = MutableStateFlow(null)
}

/**
 * Wire models of the Action Protocol (kernel -> body). The kernel sends a
 * command, the body executes it and reports the result; see
 * backend-core/app/api/routers/action.py for the server side.
 */

/** One command from the kernel, as received over WS or /pending. */
data class DeviceCommand(
    val id: String = "",
    val action: String = "",
    val params: Map<String, Any?> = emptyMap(),
)

/** Payload sent back to the kernel: {"type":"result","id":...,"status":...}. */
data class DeviceResult(
    val type: String = "result",
    val id: String,
    val status: String,          // "done" | "failed"
    val result: Any? = null,
    val error: String? = null,
)

/** The agent's connection state, surfaced to the Settings UI. */
sealed class AgentStatus {
    object Unpaired : AgentStatus()
    object Connected : AgentStatus()
    object Disconnected : AgentStatus()
    object Reconnecting : AgentStatus()
    data class ActionDone(val action: String) : AgentStatus()
}
