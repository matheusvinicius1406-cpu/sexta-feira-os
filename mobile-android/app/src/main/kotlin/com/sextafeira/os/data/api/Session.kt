package com.sextafeira.os.data.api

/**
 * Singleton holder for the current owner session.
 * Populated by [SessionManager] on login / restore.
 */
object Session {

    /** The Bearer token (JWT) for authenticated requests. null if not logged in. */
    @Volatile
    var bearer: String? = null
        private set

    /** The owner's unique ID. */
    @Volatile
    var ownerId: String? = null
        private set

    /** Whether the user is currently authenticated (has a valid token). */
    val isAuthenticated: Boolean
        get() = bearer != null

    /** Whether the token is available and looks plausible. */
    val hasValidSession: Boolean
        get() = bearer != null && bearer!!.startsWith("eyJ") // JWT starts with base64

    /**
     * Update the session with new credentials.
     * Called by [SessionManager] on login or restore.
     */
    fun set(token: String, id: String) {
        bearer = token
        ownerId = id
    }

    /** Clear the session (logout / session expired). */
    fun clear() {
        bearer = null
        ownerId = null
    }
}
