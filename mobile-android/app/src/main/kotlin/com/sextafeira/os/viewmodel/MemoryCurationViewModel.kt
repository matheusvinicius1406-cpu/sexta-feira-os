package com.sextafeira.os.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.sextafeira.os.data.api.MemoryItem
import com.sextafeira.os.data.api.RecallRequest
import com.sextafeira.os.data.api.SextaFeiraApi
import com.sextafeira.os.data.api.TeachRequest
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

// ── UI State ──────────────────────────────────────────────

data class MemoryCurationUiState(
    // List
    val memories: List<MemoryItem> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null,

    // Search
    val searchQuery: String = "",
    val searchResults: List<MemoryItem>? = null,
    val isSearching: Boolean = false,

    // Delete
    val deletingIds: Set<String> = emptySet(),

    // Teach (add new)
    val isTeaching: Boolean = false,
    val teachSuccess: String? = null,
    val teachError: String? = null,

    // Detail (selected memory)
    val selectedMemory: MemoryItem? = null,
    val detailContent: String = "",
)

// ── ViewModel ─────────────────────────────────────────────

@HiltViewModel
class MemoryCurationViewModel @Inject constructor(
    private val api: SextaFeiraApi,
) : ViewModel() {

    private val _uiState = MutableStateFlow(MemoryCurationUiState())
    val uiState: StateFlow<MemoryCurationUiState> = _uiState.asStateFlow()

    init {
        loadMemories()
    }

    // ── Load ─────────────────────────────────────────────

    fun loadMemories() {
        _uiState.update { it.copy(isLoading = true, error = null) }

        viewModelScope.launch {
            try {
                val memories = api.listMemories(limit = 200)
                _uiState.update {
                    it.copy(memories = memories, isLoading = false)
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        error = "Falha ao carregar memórias: ${e.message ?: "desconhecido"}",
                    )
                }
            }
        }
    }

    // ── Search ───────────────────────────────────────────

    fun onSearchQueryChanged(query: String) {
        _uiState.update { it.copy(searchQuery = query) }
        if (query.isBlank()) {
            _uiState.update { it.copy(searchResults = null) }
        }
    }

    fun search() {
        val query = _uiState.value.searchQuery.trim()
        if (query.isBlank()) {
            _uiState.update { it.copy(searchResults = null) }
            return
        }

        _uiState.update { it.copy(isSearching = true, error = null) }

        viewModelScope.launch {
            try {                    val results = api.recallMemory(
                        RecallRequest(
                            query = query,
                            networked = true,
                            topK = 30,
                        )
                    )
                _uiState.update {
                    it.copy(searchResults = results, isSearching = false)
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isSearching = false,
                        error = "Falha na busca: ${e.message ?: "desconhecido"}",
                    )
                }
            }
        }
    }

    fun clearSearch() {
        _uiState.update { it.copy(searchQuery = "", searchResults = null) }
    }

    // ── Forget ───────────────────────────────────────────

    fun forgetMemory(memoryId: String) {
        _uiState.update { it.copy(deletingIds = it.deletingIds + memoryId) }

        viewModelScope.launch {
            try {
                api.forgetMemory(memoryId)
                _uiState.update { state ->
                    state.copy(
                        memories = state.memories.filter { it.id != memoryId },
                        searchResults = state.searchResults?.filter { it.id != memoryId },
                        deletingIds = state.deletingIds - memoryId,
                        selectedMemory = if (state.selectedMemory?.id == memoryId) null
                                        else state.selectedMemory,
                    )
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        deletingIds = it.deletingIds - memoryId,
                        error = "Falha ao esquecer: ${e.message ?: "desconhecido"}",
                    )
                }
            }
        }
    }

    // ── Teach ────────────────────────────────────────────

    fun teachMemory(content: String, title: String?, kind: String) {
        if (content.isBlank()) return

        _uiState.update { it.copy(isTeaching = true, teachError = null, teachSuccess = null) }

        viewModelScope.launch {
            try {
                val result = api.teachMemory(
                    TeachRequest(
                        content = content.trim(),
                        title = title?.trim()?.takeIf { it.isNotBlank() },
                        kind = kind,
                    )
                )
                _uiState.update {
                    it.copy(
                        isTeaching = false,
                        teachSuccess = "✅ Memória salva: \"${result.title ?: result.content?.take(40)}\"",
                    )
                }
                // Refresh the list to show the new memory
                loadMemories()
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isTeaching = false,
                        teachError = "Falha ao ensinar: ${e.message ?: "desconhecido"}",
                    )
                }
            }
        }
    }

    fun clearTeachMessages() {
        _uiState.update { it.copy(teachSuccess = null, teachError = null) }
    }

    // ── Detail ───────────────────────────────────────────

    fun selectMemory(memory: MemoryItem) {
        _uiState.update {
            it.copy(
                selectedMemory = memory,
                detailContent = memory.content ?: "",
            )
        }
    }

    fun clearSelection() {
        _uiState.update { it.copy(selectedMemory = null, detailContent = "") }
    }
}
