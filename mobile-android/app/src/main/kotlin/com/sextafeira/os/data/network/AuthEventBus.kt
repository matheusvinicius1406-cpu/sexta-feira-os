package com.sextafeira.os.data.network

import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.receiveAsFlow

/**
 * Sealed hierarchy of authentication events.
 */
sealed class AuthEvent {
    /** The session token expired or was rejected by the server. */
    data object SessionExpired : AuthEvent()
}

/**
 * Simple event bus that emits [AuthEvent]s.
 *
 * The UI observes this via [AuthEventBus.events] and reacts accordingly
 * (e.g. redirect to login screen on session expiry).
 */
object AuthEventBus {

    private val _events = Channel<AuthEvent>(Channel.BUFFERED)

    /** Flow of auth events that the UI layer can collect. */
    val events: Flow<AuthEvent> = _events.receiveAsFlow()

    /** Emit an event to the bus (e.g. from [AuthInterceptor]). */
    fun emit(event: AuthEvent) {
        _events.trySend(event)
    }
}
