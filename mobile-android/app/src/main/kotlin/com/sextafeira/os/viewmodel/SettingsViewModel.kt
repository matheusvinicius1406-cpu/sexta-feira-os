package com.sextafeira.os.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.sextafeira.os.data.api.ApiClient
import com.sextafeira.os.data.api.DeviceInfo
import com.sextafeira.os.data.api.HealthResponse
import com.sextafeira.os.data.api.PairRequest
import com.sextafeira.os.data.api.SextaFeiraApi
import com.sextafeira.os.data.settings.SettingsRepository
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
) : ViewModel() {

    private val _uiState = MutableStateFlow(SettingsUiState())
    val uiState: StateFlow<SettingsUiState> = _uiState.asStateFlow()

    init {
        // Load persisted kernel URL
        viewModelScope.launch {
            val saved = settingsRepository.kernelUrl.first()
            _uiState.update { it.copy(kernelUrl = saved) }
        }
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
                _uiState.update {
                    it.copy(
                        isPairing = false,
                        pairingCode = "",
                        pairingSuccess = "✅ Dispositivo pareado com sucesso!",
                        pairingError = null,
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
}
