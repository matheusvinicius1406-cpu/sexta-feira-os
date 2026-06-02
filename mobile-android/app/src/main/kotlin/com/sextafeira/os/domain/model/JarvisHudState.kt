package com.sextafeira.os.domain.model

enum class JarvisMode {
    IDLE,
    LISTENING,
    THINKING,
    SPEAKING,
    EXECUTING
}

data class JarvisHudState(
    val mode: JarvisMode = JarvisMode.IDLE,
    val subtitle: String = "Aguardando ativação..."
)