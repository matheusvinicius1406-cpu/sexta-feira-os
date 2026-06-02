package com.sextafeira.os.viewmodel

import androidx.lifecycle.ViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

enum class JarvisState {
    IDLE,
    LISTENING,
    THINKING,
    SPEAKING,
    ERROR
}

data class JarvisHudState(
    val state: JarvisState = JarvisState.IDLE,
    val displayText: String = "JARVIS",
    val subtitle: String = "Aguardando ativação",
    val pulseScale: Float = 1f,
    val lastResponse: String = ""
)

class JarvisHudViewModel : ViewModel() {

    private val _uiState = MutableStateFlow(JarvisHudState())
    val uiState: StateFlow<JarvisHudState> = _uiState.asStateFlow()

    fun wakeUp() {
        _uiState.value = JarvisHudState(
            state = JarvisState.LISTENING,
            displayText = "OUVINDO",
            subtitle = "Fale seu comando",
            pulseScale = 1.15f
        )
    }

    fun startThinking() {
        _uiState.value = _uiState.value.copy(
            state = JarvisState.THINKING,
            displayText = "PROCESSANDO",
            subtitle = "Analisando solicitação",
            pulseScale = 1.25f
        )
    }

    fun startSpeaking(response: String) {
        _uiState.value = _uiState.value.copy(
            state = JarvisState.SPEAKING,
            displayText = "RESPONDENDO",
            subtitle = response.take(60),
            pulseScale = 1.35f,
            lastResponse = response
        )
    }

    fun idle() {
        _uiState.value = JarvisHudState(
            state = JarvisState.IDLE,
            displayText = "JARVIS",
            subtitle = "Pronto para ajudar",
            pulseScale = 1f,
            lastResponse = _uiState.value.lastResponse
        )
    }

    fun error(message: String) {
        _uiState.value = JarvisHudState(
            state = JarvisState.ERROR,
            displayText = "ERRO",
            subtitle = message,
            pulseScale = 1f
        )
    }
}