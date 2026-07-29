package com.sextafeira.os.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.sextafeira.os.data.api.LoginRequest
import com.sextafeira.os.data.api.Session
import com.sextafeira.os.data.api.SextaFeiraApi
import com.sextafeira.os.data.session.SessionManager
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

/** Real authentication against the local kernel. Sets the owner session on success. */
@HiltViewModel
class LoginViewModel @Inject constructor(
    private val api: SextaFeiraApi,
) : ViewModel() {

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error

    fun login(email: String, password: String, onSuccess: () -> Unit) {
        viewModelScope.launch {
            _isLoading.value = true
            _error.value = null
            try {
                val res = api.login(LoginRequest(email.trim(), password))
                // Persist to DataStore + update Session singleton.
                SessionManager.save(res.accessToken, res.ownerId)
                _isLoading.value = false
                onSuccess()
            } catch (e: Exception) {
                _isLoading.value = false
                _error.value = "Falha no login: ${e.message ?: "verifique o endereço do kernel e a senha"}"
            }
        }
    }
}
