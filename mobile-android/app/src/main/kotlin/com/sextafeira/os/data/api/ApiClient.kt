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
 */
object ApiClient {

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
     */
    fun updateBaseUrl(newUrl: String, okHttpClient: OkHttpClient): SextaFeiraApi {
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
