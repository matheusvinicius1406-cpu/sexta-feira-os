package com.sextafeira.os.data.api

import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

/**
 * Builds the [SextaFeiraApi] Retrofit instance.
 *
 * The base URL defaults to localhost (for when the backend runs on the
 * same device via Termux) and can be changed in Settings to reach a
 * remote kernel (e.g. when the backend is on a PC on the LAN).
 *
 * Security: the kernel speaks plain HTTP by design (private local service),
 * which is only acceptable when the peer is on THIS machine or the private
 * LAN. [validateKernelUrl] refuses http:// URLs pointing at public hosts —
 * sending the owner's token to a public endpoint over cleartext would leak
 * it to the internet.
 */
object ApiClient {

    private val PRIVATE_IP = Regex(
        "^(127\\.|10\\.|192\\.168\\.|172\\.(1[6-9]|2[0-9]|3[01])\\.)"
    )

    /**
     * Validate a kernel URL. Returns null when acceptable, or a message
     * explaining why not. http:// is allowed ONLY for loopback/private hosts;
     * anything public must use https.
     */
    fun validateKernelUrl(raw: String): String? {
        val url = raw.trim()
        if (url.isEmpty()) return "URL não pode estar vazia"
        val lower = url.lowercase()
        if (lower.startsWith("https://")) return null
        if (!lower.startsWith("http://")) return "Use http:// ou https://"
        val host = lower.removePrefix("http://").substringBefore('/').substringBefore(':')
        val private = host == "localhost" || host == "127.0.0.1" || host == "::1" ||
            PRIVATE_IP.containsMatchIn(host)
        return if (private) {
            null
        } else {
            "O kernel é privado: http:// só vale para esta máquina ou a rede local. " +
                "Use https:// para hosts públicos."
        }
    }

    /**
     * The base URL of the Sexta-Feira OS backend.
     * Default: localhost (backend runs on-device via Termux).
     *
     * Can be changed at runtime via [updateBaseUrl].
     */
    @Volatile
    var baseUrl: String = "http://127.0.0.1:8000"

    @Volatile
    private var retrofit: Retrofit? = null

    @Volatile
    private var api: SextaFeiraApi? = null

    /**
     * Build or rebuild the API client with the given OkHttp client.
     */
    fun buildApi(okHttpClient: OkHttpClient): SextaFeiraApi {
        val currentUrl = baseUrl.trimEnd('/') + "/"
        val newRetrofit = Retrofit.Builder()
            .baseUrl(currentUrl)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
        retrofit = newRetrofit
        val newApi = newRetrofit.create(SextaFeiraApi::class.java)
        api = newApi
        return newApi
    }

    /**
     * Update the backend base URL and rebuild the API client.
     * Call this when the user changes the server address in Settings.
     *
     * @throws IllegalArgumentException when the URL would send credentials in
     *         cleartext to a public host (see [validateKernelUrl]).
     */
    fun updateBaseUrl(newUrl: String, okHttpClient: OkHttpClient): SextaFeiraApi {
        validateKernelUrl(newUrl)?.let { throw IllegalArgumentException(it) }
        baseUrl = newUrl.trimEnd('/')
        return buildApi(okHttpClient)
    }

    /**
     * Get the current API instance. Rebuilds if null.
     */
    fun getApi(okHttpClient: OkHttpClient): SextaFeiraApi {
        return api ?: buildApi(okHttpClient)
    }
}
