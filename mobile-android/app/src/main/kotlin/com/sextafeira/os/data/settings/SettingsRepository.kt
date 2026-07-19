package com.sextafeira.os.data.settings

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.settingsStore: DataStore<Preferences> by preferencesDataStore(name = "settings")

/**
 * Persists app-wide settings to DataStore so they survive restarts.
 *
 * Currently stores the kernel base URL so the user can switch between
 * Termux (localhost), LAN, or a private tunnel without re-typing it.
 */
class SettingsRepository(private val context: Context) {

    companion object {
        private const val KEY_KERNEL_URL = "kernel_url"
        private val kernelUrlKey = stringPreferencesKey(KEY_KERNEL_URL)

        /** Default URL — localhost for on-device Termux usage. */
        const val DEFAULT_KERNEL_URL = "http://127.0.0.1:8000"
    }

    /** Flow that emits the persisted kernel URL whenever it changes. */
    val kernelUrl: Flow<String> = context.settingsStore.data.map { prefs ->
        prefs[kernelUrlKey] ?: DEFAULT_KERNEL_URL
    }

    /** One-shot read of the current kernel URL from DataStore. */
    suspend fun getKernelUrl(): String {
        return context.settingsStore.data.first()[kernelUrlKey] ?: DEFAULT_KERNEL_URL
    }

    /** Persist a new kernel URL and update [ApiClient.baseUrl]. */
    suspend fun saveKernelUrl(url: String) {
        val cleaned = url.trimEnd('/')
        context.settingsStore.edit { prefs ->
            prefs[kernelUrlKey] = cleaned
        }
        // Also update the live ApiClient so subsequent calls go to the new URL.
        com.sextafeira.os.data.api.ApiClient.baseUrl = cleaned
    }
}
