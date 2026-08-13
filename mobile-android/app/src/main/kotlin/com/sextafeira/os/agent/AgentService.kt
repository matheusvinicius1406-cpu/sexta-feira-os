package com.sextafeira.os.agent

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import com.sextafeira.os.R
import com.sextafeira.os.data.agent.ActionExecutor
import com.sextafeira.os.data.agent.ActionStreamClient
import com.sextafeira.os.data.agent.AgentMonitor
import com.sextafeira.os.data.agent.AgentSession
import com.sextafeira.os.data.agent.AgentStatus
import com.sextafeira.os.data.settings.SettingsRepository
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import timber.log.Timber
import javax.inject.Inject

/**
 * The agent's heartbeat: keeps the phone listening to the kernel's Action
 * Protocol so the brain can use this body as its hands.
 *
 * Runs as a foreground service (persistent notification) because a background
 * WebSocket would be killed within minutes on modern Android. The owner turns
 * it on in Settings after pairing; the stream client does the rest.
 */
@AndroidEntryPoint
class AgentService : Service() {

    @Inject lateinit var executor: ActionExecutor
    @Inject lateinit var settingsRepository: SettingsRepository

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var streamClient: ActionStreamClient? = null

    override fun onCreate() {
        super.onCreate()
        AgentSession.init(applicationContext)
        createChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        ServiceCompat.startForeground(
            this,
            NOTIFICATION_ID,
            buildNotification("conectando ao cérebro…"),
            ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC,
        )

        val stream = ActionStreamClient(
            executor = executor,
            baseUrlProvider = { settingsRepository.getKernelUrl() },
            deviceTokenProvider = { AgentSession.getDeviceToken() },
        )
        streamClient = stream
        stream.start(scope) { status -> updateNotification(status) }
        Timber.i("agente iniciado")
        return START_STICKY
    }

    override fun onDestroy() {
        streamClient?.stop()
        streamClient = null
        scope.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    // ── notification ───────────────────────────────────────

    private fun createChannel() {
        val nm = getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(
            NotificationChannel(
                CHANNEL_ID,
                "Agente (mãos)",
                NotificationManager.IMPORTANCE_LOW,
            ).apply { description = "O celular ouvindo o cérebro para executar ações" }
        )
        // Canal usado pelo executor quando o kernel pede uma notificação (notify).
        nm.createNotificationChannel(
            NotificationChannel(
                ActionExecutor.AGENT_CHANNEL_ID,
                "Ações do agente",
                NotificationManager.IMPORTANCE_HIGH,
            ).apply { description = "Notificações pedidas pelo cérebro" }
        )
    }

    private fun buildNotification(text: String): Notification =
        NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle("Sexta-Feira — agente ativo")
            .setContentText(text)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()

    private fun updateNotification(status: AgentStatus) {
        val label = when (status) {
            AgentStatus.Connected -> "mãos conectadas ao cérebro"
            AgentStatus.Reconnecting, AgentStatus.Disconnected -> "reconectando…"
            AgentStatus.Unpaired -> "sem pareamento"
            is AgentStatus.ActionDone -> "executou: ${status.action}"
        }
        AgentMonitor.status.value = status
        val nm = getSystemService(NotificationManager::class.java)
        nm.notify(NOTIFICATION_ID, buildNotification(label))
    }

    companion object {
        const val CHANNEL_ID = "agente"
        private const val NOTIFICATION_ID = 42

        fun start(context: Context) {
            context.startForegroundService(Intent(context, AgentService::class.java))
        }

        fun stop(context: Context) {
            context.stopService(Intent(context, AgentService::class.java))
        }
    }
}
