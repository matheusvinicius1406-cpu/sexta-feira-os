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
 * Decision (which handler, parameter normalization, validation) lives in
 * [ActionPlanner] — pure and unit-tested. This class only EXECUTES a plan
 * against the real device.
 *
 * The vocabulary is deliberately small and SAFE: it dials (never calls), opens
 * the SMS composer (never sends), opens maps (never drives) — so the owner
 * always keeps the final tap.
 */
@Singleton
class ActionExecutor @Inject constructor(
    @ApplicationContext private val context: Context,
) {

    /** Execute one command. Never throws: every failure becomes a "failed" result. */
    suspend fun execute(action: String, params: Map<String, Any?>): ActionResult {
        val plan = ActionPlanner.plan(action, params)
        if (plan.status == "failed") {
            return ActionResult("failed", error = plan.error)
        }
        return when (plan.kind) {
            ActionKind.OPEN_APP -> openApp(plan.target)
            ActionKind.NAVIGATE -> navigate(plan.target)
            ActionKind.DIAL -> dial(plan.target)
            ActionKind.SMS -> composeSms(plan.target, plan.text)
            ActionKind.NOTIFY -> notify(plan.title, plan.text, plan.id)
            ActionKind.TOAST -> toast(plan.text)
        }
    }

    // ── open_app ───────────────────────────────────────────

    private fun openApp(target: String): ActionResult {
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

    private fun navigate(query: String): ActionResult {
        val uri = Uri.parse("geo:0,0?q=${Uri.encode(query)}")
        return startExternal(Intent(Intent.ACTION_VIEW, uri)) { "navegando para: $query" }
    }

    // ── make_call ──────────────────────────────────────────

    private fun dial(number: String): ActionResult {
        // ACTION_DIAL (not ACTION_CALL): opens the dialer, no CALL_PHONE
        // permission, and the owner makes the final tap.
        val uri = Uri.parse("tel:$number")
        return startExternal(Intent(Intent.ACTION_DIAL, uri)) { "discando: $number" }
    }

    // ── send_sms ───────────────────────────────────────────

    private fun composeSms(number: String, text: String): ActionResult {
        val intent = Intent(Intent.ACTION_SENDTO, Uri.parse("smsto:$number"))
        if (text.isNotBlank()) intent.putExtra("sms_body", text)
        return startExternal(intent) { "compondo SMS para $number" }
    }

    // ── notify ─────────────────────────────────────────────

    private fun notify(title: String, body: String, id: String = ""): ActionResult {
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
            val tag = id.ifBlank { System.currentTimeMillis().toString() }
            NotificationManagerCompat.from(context).notify(tag, tag.hashCode(), notification)
            ActionResult("done", result = "notificação enviada")
        } catch (e: SecurityException) {
            ActionResult("failed", error = "sem permissão de notificação")
        } catch (e: Exception) {
            ActionResult("failed", error = e.message ?: "falha ao notificar")
        }
    }

    // ── toast ──────────────────────────────────────────────

    private fun toast(text: String): ActionResult {
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
