package com.sextafeira.os.data.agent

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.widget.Toast
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.sextafeira.os.R
import dagger.hilt.android.qualifiers.ApplicationContext
import timber.log.Timber
import javax.inject.Inject
import javax.inject.Singleton

/** Outcome of executing one device command — reported back to the kernel. */
data class ActionResult(
    val status: String,        // "done" | "failed"
    val result: String? = null,
    val error: String? = null,
)

/**
 * The phone's HANDS: turns {action, params} from the kernel into native Android
 * behavior.
 *
 * The vocabulary is deliberately small and SAFE: it dials (never calls), opens
 * the SMS composer (never sends), opens maps (never drives) — so the owner
 * always keeps the final tap. The kernel's protocol is transport, not
 * vocabulary: this class decides what each action means on THIS body, and the
 * vocabulary grows here without kernel changes.
 */
@Singleton
class ActionExecutor @Inject constructor(
    @ApplicationContext private val context: Context,
) {

    /** Execute one command. Never throws: every failure becomes a "failed" result. */
    suspend fun execute(action: String, params: Map<String, Any?>): ActionResult {
        return when (action.lowercase()) {
            "open_app", "abrir_app", "abrir" -> openApp(params)
            "navigate", "navegar" -> navigate(params)
            "make_call", "call", "ligar", "discar" -> dial(params)
            "send_sms", "sms", "message", "mensagem" -> composeSms(params)
            "notify", "show_notification", "notificar" -> notify(params)
            "toast" -> toast(params)
            else -> ActionResult("failed", error = "Ação desconhecida: '$action'")
        }
    }

    // ── open_app ───────────────────────────────────────────

    private fun openApp(params: Map<String, Any?>): ActionResult {
        val target = (params["app"] ?: params["package"] ?: params["nome"])
            ?.toString()?.trim().orEmpty()
        if (target.isBlank()) {
            return ActionResult("failed", error = "open_app sem 'app'/'package'")
        }

        val pm = context.packageManager

        // 1 — exact package name, cheapest and unambiguous.
        if (target.contains(".")) {
            pm.getLaunchIntentForPackage(target)?.let { launch ->
                return startExternal(launch) { "aberto: $target" }
            }
        }

        // 2 — match by app label (or package) among launcher apps, case-insensitive.
        val launcher = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
        val pick = pm.queryIntentActivities(launcher, 0)
            .mapNotNull { res ->
                val label = res.loadLabel(pm).toString()
                val pkg = res.activityInfo.packageName
                if (label.contains(target, ignoreCase = true) || pkg.contains(target, ignoreCase = true)) {
                    Triple(label, pkg, pm.getLaunchIntentForPackage(pkg))
                } else null
            }
            .firstOrNull { it.third != null }

        return if (pick != null) {
            startExternal(pick.third!!) { "aberto: ${pick.first}" }
        } else {
            ActionResult("failed", error = "Nenhum app encontrado para '$target'")
        }
    }

    // ── navigate ───────────────────────────────────────────

    private fun navigate(params: Map<String, Any?>): ActionResult {
        val dest = (params["destination"] ?: params["destino"] ?: params["address"] ?: params["endereco"])
            ?.toString()?.trim().orEmpty()
        val lat = params["lat"]?.toString()
        val lon = params["lon"]?.toString()

        val query = when {
            dest.isNotBlank() -> dest
            lat != null && lon != null -> "$lat,$lon"
            else -> return ActionResult("failed", error = "navigate sem 'destination' ou lat/lon")
        }

        val uri = Uri.parse("geo:0,0?q=${Uri.encode(query)}")
        return startExternal(Intent(Intent.ACTION_VIEW, uri)) { "navegando para: $query" }
    }

    // ── make_call ──────────────────────────────────────────

    private fun dial(params: Map<String, Any?>): ActionResult {
        val number = (params["number"] ?: params["phone"] ?: params["numero"])
            ?.toString()?.replace(Regex("[^0-9+*#]"), "").orEmpty()
        if (number.isBlank()) {
            return ActionResult("failed", error = "ligar sem 'number'")
        }
        // ACTION_DIAL (not ACTION_CALL): opens the dialer, no CALL_PHONE
        // permission, and the owner makes the final tap.
        val uri = Uri.parse("tel:$number")
        return startExternal(Intent(Intent.ACTION_DIAL, uri)) { "discando: $number" }
    }

    // ── send_sms ───────────────────────────────────────────

    private fun composeSms(params: Map<String, Any?>): ActionResult {
        val number = (params["number"] ?: params["phone"] ?: params["numero"])?.toString().orEmpty()
        val text = (params["text"] ?: params["message"] ?: params["mensagem"])?.toString().orEmpty()
        if (number.isBlank() && text.isBlank()) {
            return ActionResult("failed", error = "sms sem 'number'/'text'")
        }
        val intent = Intent(Intent.ACTION_SENDTO, Uri.parse("smsto:$number"))
        if (text.isNotBlank()) intent.putExtra("sms_body", text)
        return startExternal(intent) { "compondo SMS para $number" }
    }

    // ── notify ─────────────────────────────────────────────

    private fun notify(params: Map<String, Any?>): ActionResult {
        val title = (params["title"] ?: params["titulo"]).toString().ifBlank { "Sexta-Feira" }
        val body = (params["body"] ?: params["mensagem"] ?: params["text"]).toString().ifBlank { "" }

        if (Build.VERSION.SDK_INT >= 33 &&
            context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            return ActionResult("failed", error = "sem permissão de notificação")
        }

        val notification = NotificationCompat.Builder(context, AGENT_CHANNEL_ID)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .build()

        return try {
            val tag = (params["id"]?.toString() ?: System.currentTimeMillis().toString())
            NotificationManagerCompat.from(context).notify(tag, tag.hashCode(), notification)
            ActionResult("done", result = "notificação enviada")
        } catch (e: SecurityException) {
            ActionResult("failed", error = "sem permissão de notificação")
        } catch (e: Exception) {
            ActionResult("failed", error = e.message ?: "falha ao notificar")
        }
    }

    // ── toast ──────────────────────────────────────────────

    private fun toast(params: Map<String, Any?>): ActionResult {
        val text = (params["text"] ?: params["mensagem"]).toString().ifBlank { "ok" }
        Toast.makeText(context, text, Toast.LENGTH_LONG).show()
        return ActionResult("done", result = "toast: $text")
    }

    // ── helpers ────────────────────────────────────────────

    /** Launch an external intent; translate failure into a "failed" result. */
    private inline fun startExternal(intent: Intent, ok: () -> String): ActionResult {
        return try {
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(intent)
            ActionResult("done", result = ok())
        } catch (e: Exception) {
            Timber.w(e, "startActivity falhou")
            ActionResult("failed", error = e.message ?: "não foi possível abrir")
        }
    }

    companion object {
        /** Channel for notifications this body shows on the owner's behalf. */
        const val AGENT_CHANNEL_ID = "agente_acoes"
    }
}
