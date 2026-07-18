package com.sextafeira.os.data.api

import com.sextafeira.os.data.network.AuthInterceptor
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

/**
 * Central network configuration for reaching YOUR local kernel.
 *
 * IMPORTANT — the kernel runs on your machine, not on the phone:
 *  - Android emulator  -> the host machine is 10.0.2.2 (NOT localhost/127.0.0.1).
 *  - Physical device   -> use the kernel's LAN IP (e.g. http://192.168.0.10:8000)
 *                         or a private tunnel (Tailscale). Set it in Settings.
 *
 * baseUrl is a var so a Settings screen can point the app at your kernel without
 * a rebuild. Default targets the emulator's view of the host.
 */
object ApiClient {
    @Volatile
    var baseUrl: String = "http://10.0.2.2:8000/"

    @Volatile
    private var cached: Pair<String, SextaFeiraApi>? = null

    /** Build API instance with a custom OkHttpClient (used by Hilt). */
    fun buildApi(client: OkHttpClient): SextaFeiraApi {
        return Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(SextaFeiraApi::class.java)
    }

    val api: SextaFeiraApi
        get() {
            cached?.let { (url, svc) -> if (url == baseUrl) return svc }
            val http = OkHttpClient.Builder()
                .connectTimeout(15, TimeUnit.SECONDS)
                .readTimeout(120, TimeUnit.SECONDS)
                .addInterceptor(AuthInterceptor())
                .build()
            val svc = buildApi(http)
            cached = baseUrl to svc
            return svc
        }
}

/** Holds the owner's session token for the lifetime of the app process. */
object Session {
    @Volatile
    var token: String? = null
        private set

    @Volatile
    var ownerId: String? = null
        private set

    /** Set memory only (no DataStore persist). Use SessionManager.save() for persistence. */
    fun set(token: String, ownerId: String) {
        this.token = token
        this.ownerId = ownerId
    }

    /** Set memory only (called by SessionManager when loading from DataStore). */
    fun restore(token: String, ownerId: String) {
        this.token = token
        this.ownerId = ownerId
    }

    fun clear() {
        token = null
        ownerId = null
    }

    val bearer: String? get() = token?.let { "Bearer $it" }
    val isAuthenticated: Boolean get() = token != null
}
