package com.sextafeira.os.data.network

import okhttp3.Interceptor
import okhttp3.Response

/**
 * OkHttp [Interceptor] that watches every HTTP response for 401 Unauthorized.
 *
 * When the kernel rejects the token (expired JWT, kernel restarted with a new
 * secret key, or device was revoked), we clear the local session and emit a
 * [AuthEvent.SessionExpired] so the UI can redirect to the Login screen.
 */
class AuthInterceptor : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        val response = chain.proceed(request)

        if (response.code == 401) {
            AuthEventBus.onSessionExpired()
        }

        return response
    }
}
