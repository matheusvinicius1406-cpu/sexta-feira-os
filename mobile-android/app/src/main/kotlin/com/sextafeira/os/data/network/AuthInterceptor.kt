package com.sextafeira.os.data.network

import com.sextafeira.os.data.api.Session
import okhttp3.Interceptor
import okhttp3.Response
import timber.log.Timber

/**
 * OkHttp interceptor that automatically attaches the JWT Bearer token
 * to every authenticated request.
 *
 * If the token is missing for a protected endpoint, the request proceeds
 * without auth — the server will return 401 and the [AuthEventBus] will
 * notify the UI to redirect to login.
 */
class AuthInterceptor : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val original = chain.request()
        val bearer = Session.bearer

        // If we have a token, attach it
        val request = if (bearer != null) {
            original.newBuilder()
                .header("Authorization", bearer)
                .build()
        } else {
            original
        }

        val response = chain.proceed(request)

        // If server returned 401, broadcast session expired
        if (response.code == 401 && bearer != null) {
            Timber.w("AuthInterceptor: received 401 — session expired")
            Session.clear()
            AuthEventBus.emit(AuthEvent.SessionExpired)
        }

        return response
    }
}
