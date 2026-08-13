package com.sextafeira.os.data.agent

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

private val Context.agentStore: DataStore<Preferences> by preferencesDataStore(name = "agent")

/**
 * The device's own identity on the kernel — the long-lived device token and id
 * issued at pairing (POST /api/v1/auth/devices/pair).
 *
 * This is what makes the phone a BODY ("as mãos"): the agent authenticates as
 * THIS device to receive action commands, as opposed to the owner session in
 * [com.sextafeira.os.data.api.Session], which is the person.
 */
object AgentSession {

    private const val KEY_DEVICE_TOKEN = "device_token"
    private const val KEY_DEVICE_ID = "device_id"

    private val deviceTokenKey = stringPreferencesKey(KEY_DEVICE_TOKEN)
    private val deviceIdKey = stringPreferencesKey(KEY_DEVICE_ID)

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    @Volatile
    private var store: DataStore<Preferences>? = null

    /** Whether this phone is paired (has a device token) — the agent can run. */
    @Volatile
    var isPaired: Boolean = false
        private set

    /** Restore the persisted pairing. Call once from MainActivity.onCreate. */
    fun init(context: Context) {
        if (store != null) return // already initialized
        store = context.agentStore
        scope.launch {
            val prefs = store!!.data.first()
            isPaired = prefs[deviceTokenKey] != null
        }
    }

    /** The device JWT used on the /api/v1/actions endpoints (query param for WS, Bearer for REST). */
    suspend fun getDeviceToken(): String? =
        store?.data?.first()?.get(deviceTokenKey)

    suspend fun getDeviceId(): String? =
        store?.data?.first()?.get(deviceIdKey)

    /** Persist the pair response so the agent can authenticate as this body. */
    fun save(deviceToken: String, deviceId: String) {
        isPaired = true
        scope.launch {
            store?.edit { prefs ->
                prefs[deviceTokenKey] = deviceToken
                prefs[deviceIdKey] = deviceId
            }
        }
    }

    /** Forget the pairing (device revoked or user asked to unpair). */
    fun clear() {
        isPaired = false
        scope.launch {
            store?.edit { prefs ->
                prefs.remove(deviceTokenKey)
                prefs.remove(deviceIdKey)
            }
        }
    }
}
