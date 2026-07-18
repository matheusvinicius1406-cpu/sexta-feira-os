package com.sextafeira.os.data.session

import android.content.Context
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.sextafeira.os.data.api.Session
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking

/**
 * Persists the owner session (JWT + ownerId) to DataStore so it survives
 * process restarts. On init() loads any saved session into the Session singleton.
 *
 * Usage:
 *   // On app start (MainActivity):
 *   SessionManager.init(applicationContext)
 *
 *   // After successful login:
 *   SessionManager.save(accessToken, ownerId)
 *
 *   // On logout:
 *   SessionManager.clear()
 */
private val Context.sessionStore: DataStore<Preferences> by preferencesDataStore(
    name = "sexta_session"
)

object SessionManager {
    private val TOKEN_KEY = stringPreferencesKey("auth_token")
    private val OWNER_ID_KEY = stringPreferencesKey("owner_id")

    private var _context: Context? = null
    private val context: Context
        get() = _context
            ?: throw IllegalStateException("SessionManager.init() must be called before use")

    /** Initialise with application context and load any saved session. */
    fun init(applicationContext: Context) {
        _context = applicationContext.applicationContext
        loadIntoSession()
    }

    /** Read persisted token/ownerId into the Session singleton (blocking, fast local read). */
    private fun loadIntoSession() {
        val prefs = runBlocking { context.sessionStore.data.first() }
        val token = prefs[TOKEN_KEY]
        val ownerId = prefs[OWNER_ID_KEY]
        if (token != null && ownerId != null) {
            Session.restore(token, ownerId)
        }
    }

    /** Persist token + ownerId and update the Session singleton. */
    suspend fun save(token: String, ownerId: String) {
        context.sessionStore.edit { prefs ->
            prefs[TOKEN_KEY] = token
            prefs[OWNER_ID_KEY] = ownerId
        }
        Session.restore(token, ownerId)
    }

    /** Clear persisted data and the Session singleton. */
    suspend fun clear() {
        context.sessionStore.edit { prefs ->
            prefs.remove(TOKEN_KEY)
            prefs.remove(OWNER_ID_KEY)
        }
        Session.clear()
    }
}
