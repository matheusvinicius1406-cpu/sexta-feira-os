package com.sextafeira.os.data.network

import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow

/**
 * Global event bus for authentication-related events.
 *
 * The [AuthInterceptor] fires [SessionExpired] when the kernel returns 401.
 * The navigation layer observes this flow and redirects to the Login screen.
 */
sealed class AuthEvent {
    /** The kernel rejected the current token — likely expired or invalidated by restart. */
    data object SessionExpired : AuthEvent()
}

object AuthEventBus {
    private val _events = MutableSharedFlow<AuthEvent>(extraBufferCapacity = 3)
    val events: SharedFlow<AuthEvent> = _events.asSharedFlow()

    /** Called by [AuthInterceptor] when HTTP 401 is detected. */
    fun onSessionExpired() {
        _events.tryEmit(AuthEvent.SessionExpired)
    }
}
