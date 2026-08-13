package com.sextafeira.os.viewmodel

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.sextafeira.os.agent.AgentService
import com.sextafeira.os.data.agent.AgentMonitor
import com.sextafeira.os.data.agent.AgentSession
import com.sextafeira.os.data.agent.AgentStatus
import com.sextafeira.os.data.api.ApiClient
import com.sextafeira.os.data.api.DeviceInfo
import com.sextafeira.os.data.api.HealthResponse
import com.sextafeira.os.data.api.PairRequest
import com.sextafeira.os.data.api.SecurityAuditResponse
import com.sextafeira.os.data.api.SecurityThreat
import com.sextafeira.os.data.api.SextaFeiraApi
import com.sextafeira.os.data.settings.SettingsRepository
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import retrofit2.HttpException
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit
import javax.inject.Inject

// ── UI State ──────────────────────────────────────────────

data class SettingsUiState(
    // Kernel URL
    val kernelUrl: String = SettingsRepository.DEFAULT_KERNEL_URL,
    val connectionStatus: ConnectionStatus = ConnectionStatus.UNKNOWN,
    val connectionError: String? = null,

    // Pairing
    val pairingCode: String = "",
    val isPairing: Boolean = false,
    val pairingError: String? = null,
    val pairingSuccess: String? = null,

    // Devices
    val devices: List<DeviceInfo> = emptyList(),
    val isLoadingDevices: Boolean = false,
    val deviceError: String? = null,

    // Loading state for connection test
    val isTestingConnection: Boolean = false,

    // Toggles (local state, persisted in-memory for now)
    val voiceEnabled: Boolean = true,
    val memoryEnabled: Boolean = true,
    val automationEnabled: Boolean = true,

    // Agente (mãos)
    val agentPaired: Boolean = false,
    val agentEnabled: Boolean = false,
    val agentStatus: String? = null,

    // Segurança (defesa ativa)
    val isSecurityLoading: Boolean = false,
    val securityAudit: SecurityAuditResponse? = null,
    val securityThreats: List<SecurityThreat> = emptyList(),
    val securityError: String? = null,
)

enum class ConnectionStatus {
    UNKNOWN,
    CHECKING,
    ONLINE,
    OFFLINE,
}

// ── ViewModel ─────────────────────────────────────────────

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val settingsRepository: SettingsRepository,
    private val api: SextaFeiraApi,
    private val okHttpClient: OkHttpClient,
    @ApplicationContext private val context: Context,
) : ViewModel() {

    private val _uiState = MutableStateFlow(SettingsUiState())
    val uiState: StateFlow<SettingsUiState> = _uiState.asStateFlow()

    init {
        // Load persisted kernel URL
        viewModelScope.launch {
            val saved = settingsRepository.kernelUrl.first()
            _uiState.update { it.copy(kernelUrl = saved) }
        }
        // Restore device pairing + follow the agent's live status
        AgentSession.init(context.applicationContext)
        viewModelScope.launch {
            _uiState.update { it.copy(agentPaired = AgentSession.getDeviceToken() != null) }
        }
        viewModelScope.launch {
            AgentMonitor.status.collect { s ->
                _uiState.update { it.copy(agentStatus = describeAgent(s)) }
            }
        }
    }

    private fun describeAgent(status: AgentStatus?): String? = when (status) {
        null -> null
        AgentStatus.Connected -> "conectado ao cérebro"
        AgentStatus.Reconnecting, AgentStatus.Disconnected -> "reconectando…"
        AgentStatus.Unpaired -> "sem pareamento — pareie o dispositivo"
        is AgentStatus.ActionDone -> "executou: ${status.action}"
    }

    // ── Kernel URL ────────────────────────────────────────

    fun onKernelUrlChanged(url: String) {
        _uiState.update { it.copy(kernelUrl = url, connectionStatus = ConnectionStatus.UNKNOWN) }
    }

    /** Test connection to the kernel at the given URL and optionally save it. */
    fun testConnection(saveOnSuccess: Boolean = false) {
        val url = _uiState.value.kernelUrl.trimEnd('/')
        if (url.isBlank()) {
            _uiState.update { it.copy(connectionError = "URL não pode estar vazia") }
            return
        }

        _uiState.update {
            it.copy(
                isTestingConnection = true,
                connectionStatus = ConnectionStatus.CHECKING,
                connectionError = null,
            )
        }

        viewModelScope.launch {
            try {
                // Build a temporary Retrofit client with short timeout to test
                val testClient = OkHttpClient.Builder()
                    .connectTimeout(5, TimeUnit.SECONDS)
                    .readTimeout(5, TimeUnit.SECONDS)
                    .build()

                val testApi = Retrofit.Builder()
                    .baseUrl("$url/")
                    .client(testClient)
                    .addConverterFactory(GsonConverterFactory.create())
                    .build()
                    .create(SextaFeiraApi::class.java)

                val health: HealthResponse = testApi.health()

                _uiState.update {
                    it.copy(
                        isTestingConnection = false,
                        connectionStatus = ConnectionStatus.ONLINE,
                        connectionError = null,
                    )
                }

                if (saveOnSuccess) {
                    settingsRepository.saveKernelUrl(url)
                    // Update the DI-provided API client base URL
                    ApiClient.updateBaseUrl(url, okHttpClient)
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isTestingConnection = false,
                        connectionStatus = ConnectionStatus.OFFLINE,
                        connectionError = "Falha ao conectar: ${e.message ?: "desconhecido"}",
                    )
                }
            }
        }
    }

    /** Save the URL without testing first. */
    fun saveUrl() {
        val url = _uiState.value.kernelUrl.trimEnd('/')
        viewModelScope.launch {
            settingsRepository.saveKernelUrl(url)
            ApiClient.updateBaseUrl(url, okHttpClient)
            _uiState.update { it.copy(connectionError = null) }
        }
    }

    // ── Device Pairing ────────────────────────────────────

    fun onPairingCodeChanged(code: String) {
        _uiState.update { it.copy(pairingCode = code, pairingError = null, pairingSuccess = null) }
    }

    fun pairDevice() {
        val code = _uiState.value.pairingCode.trim()
        if (code.isBlank()) {
            _uiState.update { it.copy(pairingError = "Digite o código de pareamento") }
            return
        }

        _uiState.update { it.copy(isPairing = true, pairingError = null, pairingSuccess = null) }

        viewModelScope.launch {
            try {
                val res = api.pairDevice(
                    PairRequest(
                        pairingCode = code,
                        deviceName = android.os.Build.MODEL,
                        deviceKind = "phone",
                    )
                )
                // This phone is now a BODY: keep the device token for the agent.
                AgentSession.save(res.deviceToken, res.deviceId)
                _uiState.update {
                    it.copy(
                        isPairing = false,
                        pairingCode = "",
                        pairingSuccess = "✅ Dispositivo pareado com sucesso!",
                        pairingError = null,
                        agentPaired = true,
                    )
                }
                // Refresh device list after successful pairing
                loadDevices()
            } catch (e: Exception) {
                val statusCode = (e as? HttpException)?.code()
                val msg = when (statusCode) {
                    401 -> "Código de pareamento inválido"
                    403 -> "Pareamento desativado no servidor"
                    else -> "Falha ao parear: ${e.message ?: "desconhecido"}"
                }
                _uiState.update {
                    it.copy(isPairing = false, pairingError = msg)
                }
            }
        }
    }

    // ── Device Management ─────────────────────────────────

    fun loadDevices() {
        _uiState.update { it.copy(isLoadingDevices = true, deviceError = null) }

        viewModelScope.launch {
            try {
                val devices = api.listDevices()
                _uiState.update {
                    it.copy(devices = devices, isLoadingDevices = false)
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isLoadingDevices = false,
                        deviceError = "Falha ao carregar dispositivos: ${e.message ?: "desconhecido"}",
                    )
                }
            }
        }
    }

    fun revokeDevice(deviceId: String) {
        viewModelScope.launch {
            try {
                api.revokeDevice(deviceId)
                // Refresh the device list
                loadDevices()
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(deviceError = "Falha ao revogar: ${e.message ?: "desconhecido"}")
                }
            }
        }
    }

    // ── Toggles ───────────────────────────────────────────

    fun onVoiceEnabledChanged(enabled: Boolean) {
        _uiState.update { it.copy(voiceEnabled = enabled) }
    }

    fun onMemoryEnabledChanged(enabled: Boolean) {
        _uiState.update { it.copy(memoryEnabled = enabled) }
    }

    fun onAutomationEnabledChanged(enabled: Boolean) {
        _uiState.update { it.copy(automationEnabled = enabled) }
    }

    // ── Agente (mãos) ─────────────────────────────────────

    /** Start/stop the agent foreground service. */
    fun toggleAgent(enabled: Boolean) {
        _uiState.update { it.copy(agentEnabled = enabled) }
        if (enabled) {
            AgentService.start(context.applicationContext)
        } else {
            AgentService.stop(context.applicationContext)
        }
    }

    /** User tried to enable the agent before pairing. */
    fun agentBlocked(message: String) {
        _uiState.update { it.copy(agentStatus = message, agentEnabled = false) }
    }

    // ── Segurança (defesa ativa) ────────────────────────

    /** Run the kernel's security audit (posture report) and show it. */
    fun runSecurityAudit() {
        _uiState.update { it.copy(isSecurityLoading = true, securityError = null) }
        viewModelScope.launch {
            try {
                val audit = api.securityAudit()
                _uiState.update {
                    it.copy(isSecurityLoading = false, securityAudit = audit)
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isSecurityLoading = false,
                        securityError = "Falha na auditoria: ${e.message ?: "desconhecido"}",
                    )
                }
            }
        }
    }

    /** Pull the threat trail — every tripwire that fired. */
    fun loadSecurityThreats() {
        _uiState.update { it.copy(isSecurityLoading = true, securityError = null) }
        viewModelScope.launch {
            try {
                val threats = api.securityThreats(limite = 20)
                _uiState.update {
                    it.copy(isSecurityLoading = false, securityThreats = threats)
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isSecurityLoading = false,
                        securityError = "Falha ao buscar ameaças: ${e.message ?: "desconhecido"}",
                    )
                }
            }
        }
    }
}
