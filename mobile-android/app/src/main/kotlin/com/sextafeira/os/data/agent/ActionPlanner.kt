package com.sextafeira.os.data.agent

/**
 * Pure decision logic of the phone's HANDS — no Android framework calls, so it
 * is unit-testable on the JVM.
 *
 * `ActionPlanner.plan(action, params)` normalizes the kernel's {action, params}
 * into a [PlannedAction]: which handler should run, with which validated data,
 * or a validation failure. [ActionExecutor] then executes the plan against the
 * real device (intents, notifications, toasts). Splitting decision from
 * execution keeps the safety vocabulary ("dials, never calls; composes, never
 * sends") provable in tests.
 */
object ActionPlanner {

    /** The one phone number format the dialer accepts. */
    private val DIGITS_ONLY = Regex("[^0-9+*#]")

    fun plan(action: String, params: Map<String, Any?>): PlannedAction {
        return when (action.lowercase()) {
            "open_app", "abrir_app", "abrir" -> openApp(params)
            "navigate", "navegar" -> navigate(params)
            "make_call", "call", "ligar", "discar" -> dial(params)
            "send_sms", "sms", "message", "mensagem" -> composeSms(params)
            "notify", "show_notification", "notificar" -> notify(params)
            "toast" -> toast(params)
            else -> PlannedAction.failed("Ação desconhecida: '$action'")
        }
    }

    // ── handlers ───────────────────────────────────────────

    private fun openApp(params: Map<String, Any?>): PlannedAction {
        val target = (params["app"] ?: params["package"] ?: params["nome"])
            ?.toString()?.trim().orEmpty()
        if (target.isBlank()) {
            return PlannedAction.failed("open_app sem 'app'/'package'")
        }
        return PlannedAction(kind = ActionKind.OPEN_APP, target = target)
    }

    private fun navigate(params: Map<String, Any?>): PlannedAction {
        val dest = (params["destination"] ?: params["destino"] ?: params["address"] ?: params["endereco"])
            ?.toString()?.trim().orEmpty()
        val lat = params["lat"]?.toString()
        val lon = params["lon"]?.toString()

        val query = when {
            dest.isNotBlank() -> dest
            lat != null && lon != null -> "$lat,$lon"
            else -> return PlannedAction.failed("navigate sem 'destination' ou lat/lon")
        }
        return PlannedAction(kind = ActionKind.NAVIGATE, target = query)
    }

    private fun dial(params: Map<String, Any?>): PlannedAction {
        val number = (params["number"] ?: params["phone"] ?: params["numero"])
            ?.toString()?.replace(DIGITS_ONLY, "").orEmpty()
        if (number.isBlank()) {
            return PlannedAction.failed("ligar sem 'number'")
        }
        return PlannedAction(kind = ActionKind.DIAL, target = number)
    }

    private fun composeSms(params: Map<String, Any?>): PlannedAction {
        val number = (params["number"] ?: params["phone"] ?: params["numero"])?.toString().orEmpty()
        val text = (params["text"] ?: params["message"] ?: params["mensagem"])?.toString().orEmpty()
        if (number.isBlank() && text.isBlank()) {
            return PlannedAction.failed("sms sem 'number'/'text'")
        }
        return PlannedAction(kind = ActionKind.SMS, target = number, text = text)
    }

    private fun notify(params: Map<String, Any?>): PlannedAction {
        // `.toString()` on a null Any? yields the string "null" — the original
        // executor showed literal "null" titles/bodies when a param was missing.
        val title = (params["title"] ?: params["titulo"])?.toString().orEmpty().ifBlank { "Sexta-Feira" }
        val body = (params["body"] ?: params["mensagem"] ?: params["text"])?.toString().orEmpty()
        val id = params["id"]?.toString() ?: ""
        return PlannedAction(kind = ActionKind.NOTIFY, title = title, text = body, id = id)
    }

    private fun toast(params: Map<String, Any?>): PlannedAction {
        val text = (params["text"] ?: params["mensagem"])?.toString().orEmpty().ifBlank { "ok" }
        return PlannedAction(kind = ActionKind.TOAST, text = text)
    }
}

/** Which native behavior a command maps to. */
enum class ActionKind {
    OPEN_APP, NAVIGATE, DIAL, SMS, NOTIFY, TOAST,
}

/**
 * The result of planning: a validated command ready for execution, or a
 * validation failure (status "failed").
 */
data class PlannedAction(
    val kind: ActionKind,
    /** app name/package, navigation query, phone number, SMS recipient. */
    val target: String = "",
    /** SMS body, toast text, notification body. */
    val text: String = "",
    val title: String = "",
    /** Command id (notification dedup tag). */
    val id: String = "",
    val status: String = "done",
    val error: String? = null,
) {
    companion object {
        fun failed(error: String): PlannedAction =
            PlannedAction(kind = ActionKind.TOAST, status = "failed", error = error)
    }
}
