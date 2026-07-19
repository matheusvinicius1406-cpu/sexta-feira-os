package com.sextafeira.os.data.session

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.sextafeira.os.data.api.Session
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

// Extension property for DataStore
private val Context.tokenStore: DataStore<Preferences> by preferencesDataStore(name = "session")

/**
 * Manages the owner session using DataStore.
 *
 * - Persists the JWT token + owner ID across app restarts.
 - - Restores [Session] singleton on init.
 * - Clears on logout / session expiry.
 *
 * Usage:
 *   SessionManager.init(applicationContext)  // call once in MainActivity.onCreate
 */
object SessionManager {

    private const val KEY_ACCESS_TOKEN = "access_token"
    private const val KEY_OWNER_ID = "owner_id"

    private val accessTokenKey = stringPreferencesKey(KEY_ACCESS_TOKEN)
    private val ownerIdKey = stringPreferencesKey(KEY_OWNER_ID)

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    @Volatile
    private var store: DataStore<Preferences>? = null

    /**
     * Initialize the session manager. Call once from [MainActivity.onCreate].
     * Restores the persisted session into the [Session] singleton.
     */
    fun init(context: Context) {
        if (store != null) return // already initialized

        store = context.tokenStore

        // Restore session from DataStore
        scope.launch {
            val prefs = store!!.data.first()
            val token = prefs[accessTokenKey]
            val ownerId = prefs[ownerIdKey]

            if (token != null && ownerId != null) {
                Session.set(token, ownerId)
            }
        }
    }

    /**
     * Persist a new session (called after successful login).
     */
    fun save(accessToken: String, ownerId: String) {
        Session.set(accessToken, ownerId)
        scope.launch {
            store?.edit { prefs ->
                prefs[accessTokenKey] = accessToken
                prefs[ownerIdKey] = ownerId
            }
        }
    }

    /**
     * Clear the session (logout / session expiry).
     */
    fun clear() {
        Session.clear()
        scope.launch {
            store?.edit { prefs ->
                prefs.remove(accessTokenKey)
                prefs.remove(ownerIdKey)
            }
        }
    }
}
