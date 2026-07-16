package com.sextafeira.os.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.sextafeira.os.data.api.ApiClient
import com.sextafeira.os.data.api.LoginRequest
import com.sextafeira.os.data.api.Session
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

/** Real authentication against the local kernel. Sets the owner session on success. */
class LoginViewModel : ViewModel() {

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error

    fun login(email: String, password: String, onSuccess: () -> Unit) {
        viewModelScope.launch {
            _isLoading.value = true
            _error.value = null
            try {
                val res = ApiClient.api.login(LoginRequest(email.trim(), password))
                Session.set(res.access_token, res.owner_id)
                _isLoading.value = false
                onSuccess()
            } catch (e: Exception) {
                _isLoading.value = false
                _error.value = "Falha no login: ${e.message ?: "verifique o endereço do kernel e a senha"}"
            }
        }
    }
}
