@file:OptIn(ExperimentalMaterial3Api::class)

package com.sextafeira.os.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material.icons.filled.Bookmark
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Lightbulb
import androidx.compose.material.icons.filled.Memory
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Divider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SuggestionChip
import androidx.compose.material3.SuggestionChipDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.runtime.collectAsState
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import com.sextafeira.os.data.api.MemoryItem
import com.sextafeira.os.viewmodel.MemoryCurationViewModel

@Composable
fun MemoryCurationScreen(
    navController: NavHostController,
    viewModel: MemoryCurationViewModel = hiltViewModel(),
) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            Icons.Filled.Memory,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(24.dp)
                        )
                        Spacer(Modifier.width(10.dp))
                        Text(
                            "Memória",
                            fontWeight = FontWeight.Bold,
                            fontSize = 22.sp,
                        )
                    }
                },
                navigationIcon = {
                    IconButton(onClick = { navController.popBackStack() }) {
                        Icon(
                            Icons.Filled.ArrowBack,
                            contentDescription = "Voltar",
                            tint = MaterialTheme.colorScheme.primary,
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface,
                ),
            )
        },
        containerColor = MaterialTheme.colorScheme.background,
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
        ) {
            // ── Search + Add Section ─────────────────────
            SearchAndAddBar(uiState, viewModel)

            Spacer(Modifier.height(12.dp))

            // ── Error Message ────────────────────────────
            AnimatedVisibility(
                visible = uiState.error != null,
                enter = fadeIn() + expandVertically(),
                exit = fadeOut() + shrinkVertically(),
            ) {
                Card(
                    modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp),
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.errorContainer,
                    ),
                ) {
                    Row(
                        modifier = Modifier.padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            text = uiState.error ?: "",
                            color = MaterialTheme.colorScheme.onErrorContainer,
                            fontSize = 13.sp,
                            modifier = Modifier.weight(1f),
                        )
                        TextButton(onClick = { viewModel.loadMemories() }) {
                            Text("Tentar novamente", fontSize = 12.sp)
                        }
                    }
                }
            }

            // ── Content Area ─────────────────────────────
            if (uiState.selectedMemory != null) {
                MemoryDetailView(
                    memory = uiState.selectedMemory!!,
                    onDismiss = { viewModel.clearSelection() },
                    onForget = { viewModel.forgetMemory(uiState.selectedMemory!!.id) },
                )
            } else {
                MemoryListView(uiState, viewModel)
            }
        }
    }
}

// ═══════════════════════════════════════════════════════════
// Sub-components
// ═══════════════════════════════════════════════════════════

@Composable
private fun SearchAndAddBar(
    uiState: com.sextafeira.os.viewmodel.MemoryCurationUiState,
    viewModel: MemoryCurationViewModel,
) {
    var showTeachDialog by remember { mutableStateOf(false) }
    var expanded by remember { mutableStateOf(false) }

    Column {
        // Search row
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            OutlinedTextField(
                value = uiState.searchQuery,
                onValueChange = { viewModel.onSearchQueryChanged(it) },
                placeholder = { Text("Buscar nas memórias...") },
                leadingIcon = {
                    Icon(
                        Icons.Filled.Search,
                        contentDescription = "Buscar",
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(20.dp),
                    )
                },
                trailingIcon = {
                    if (uiState.searchQuery.isNotBlank()) {
                        IconButton(onClick = { viewModel.clearSearch() }) {
                            Icon(
                                Icons.Filled.Clear,
                                contentDescription = "Limpar",
                                modifier = Modifier.size(18.dp),
                            )
                        }
                    }
                },
                singleLine = true,
                modifier = Modifier.weight(1f),
                shape = RoundedCornerShape(12.dp),
            )

            // Search button
            FilledTonalButton(
                onClick = { viewModel.search() },
                enabled = uiState.searchQuery.isNotBlank() && !uiState.isSearching,
                modifier = Modifier.height(52.dp),
                shape = RoundedCornerShape(12.dp),
            ) {
                if (uiState.isSearching) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(18.dp),
                        strokeWidth = 2.dp,
                    )
                } else {
                    Icon(Icons.Filled.Search, contentDescription = "Buscar", modifier = Modifier.size(18.dp))
                }
            }

            // Teach button
            FilledTonalButton(
                onClick = { showTeachDialog = true },
                modifier = Modifier.height(52.dp),
                shape = RoundedCornerShape(12.dp),
            ) {
                Icon(Icons.Filled.Add, contentDescription = "Ensinar", modifier = Modifier.size(18.dp))
            }
        }

        // Quick filter chips
        Row(
            modifier = Modifier.padding(vertical = 8.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            SuggestionChip(
                onClick = { viewModel.clearSearch(); viewModel.loadMemories() },
                label = { Text("Todas", fontSize = 12.sp) },
                shape = RoundedCornerShape(20.dp),
            )
            SuggestionChip(
                onClick = {
                    viewModel.onSearchQueryChanged("")
                    viewModel.search()
                },
                label = { Text("Fatos", fontSize = 12.sp) },
                shape = RoundedCornerShape(20.dp),
            )
            SuggestionChip(
                onClick = { viewModel.onSearchQueryChanged("preferência"); viewModel.search() },
                label = { Text("Preferências", fontSize = 12.sp) },
                shape = RoundedCornerShape(20.dp),
            )
        }

        // Teach dialog
        if (showTeachDialog) {
            TeachMemoryDialog(
                onDismiss = { showTeachDialog = false },
                onTeach = { content, title, kind ->
                    viewModel.teachMemory(content, title, kind)
                    showTeachDialog = false
                },
                isTeaching = uiState.isTeaching,
            )
        }

        // Teach success message
        AnimatedVisibility(
            visible = uiState.teachSuccess != null,
            enter = fadeIn() + expandVertically(),
            exit = fadeOut() + shrinkVertically(),
        ) {
            Card(
                modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.tertiaryContainer,
                ),
            ) {
                Row(
                    modifier = Modifier.padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = uiState.teachSuccess ?: "",
                        color = MaterialTheme.colorScheme.onTertiaryContainer,
                        fontSize = 13.sp,
                        modifier = Modifier.weight(1f),
                    )
                    TextButton(onClick = { viewModel.clearTeachMessages() }) {
                        Text("OK", fontSize = 12.sp)
                    }
                }
            }
        }
    }
}

@Composable
private fun MemoryListView(
    uiState: com.sextafeira.os.viewmodel.MemoryCurationUiState,
    viewModel: MemoryCurationViewModel,
) {
    val memories = uiState.searchResults ?: uiState.memories
    val listState = rememberLazyListState()

    if (uiState.isLoading) {
        Box(
            modifier = Modifier.fillMaxSize(),
            contentAlignment = Alignment.Center,
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                CircularProgressIndicator(modifier = Modifier.size(36.dp))
                Spacer(Modifier.height(12.dp))
                Text(
                    "Carregando memórias...",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    fontSize = 14.sp,
                )
            }
        }
    } else if (memories.isEmpty()) {
        Box(
            modifier = Modifier.fillMaxSize(),
            contentAlignment = Alignment.Center,
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Icon(
                    Icons.Filled.Memory,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.3f),
                    modifier = Modifier.size(64.dp),
                )
                Spacer(Modifier.height(16.dp))
                Text(
                    "Nenhuma memória encontrada",
                    color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f),
                    fontSize = 16.sp,
                )
                Text(
                    if (uiState.searchResults != null) "Tente outra busca"
                    else "Converse com o kernel para criar memórias",
                    color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.4f),
                    fontSize = 13.sp,
                )
            }
        }
    } else {
        // Search results header
        if (uiState.searchResults != null) {
            Row(
                modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    "${memories.size} resultado(s) para \"${uiState.searchQuery}\"",
                    fontSize = 13.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                TextButton(onClick = { viewModel.clearSearch() }) {
                    Text("Limpar busca", fontSize = 12.sp)
                }
            }
        }

        LazyColumn(
            state = listState,
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            // Search hint
            if (uiState.searchResults == null && uiState.memories.isNotEmpty()) {
                item {
                    Text(
                        "${uiState.memories.size} memórias armazenadas",
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f),
                        modifier = Modifier.padding(vertical = 4.dp),
                    )
                }
            }

            items(memories, key = { it.id }) { memory ->
                MemoryCard(
                    memory = memory,
                    isDeleting = memory.id in uiState.deletingIds,
                    onClick = { viewModel.selectMemory(memory) },
                    onForget = { viewModel.forgetMemory(memory.id) },
                )
            }

            // Bottom spacer
            item { Spacer(Modifier.height(16.dp)) }
        }
    }
}

@Composable
private fun MemoryCard(
    memory: MemoryItem,
    isDeleting: Boolean,
    onClick: () -> Unit,
    onForget: () -> Unit,
) {
    var showDeleteConfirm by remember { mutableStateOf(false) }

    val alphaValue by animateColorAsState(
        targetValue = if (isDeleting) MaterialTheme.colorScheme.error.copy(alpha = 0.3f)
                      else MaterialTheme.colorScheme.surface,
        animationSpec = tween(300),
        label = "deleteBg",
    )

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(enabled = !isDeleting) { onClick() },
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(
            containerColor = alphaValue,
        ),
        elevation = CardDefaults.cardElevation(
            defaultElevation = if (isDeleting) 0.dp else 1.dp,
        ),
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            verticalAlignment = Alignment.Top,
        ) {
            // Kind icon
            Box(
                modifier = Modifier
                    .size(36.dp)
                    .background(
                        color = kindColor(memory.kind).copy(alpha = 0.12f),
                        shape = RoundedCornerShape(10.dp),
                    ),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    kindIcon(memory.kind),
                    contentDescription = memory.kind,
                    tint = kindColor(memory.kind),
                    modifier = Modifier.size(18.dp),
                )
            }

            Spacer(Modifier.width(12.dp))

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = memory.title ?: memory.content?.take(60) ?: "Sem título",
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSurface,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )

                if (!memory.content.isNullOrBlank()) {
                    Text(
                        text = memory.content.take(120) +
                               if (memory.content.length > 120) "..." else "",
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.padding(top = 4.dp),
                    )
                }

                Spacer(Modifier.height(6.dp))

                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    // Kind badge
                    Text(
                        text = memory.kind,
                        fontSize = 10.sp,
                        color = kindColor(memory.kind),
                        fontWeight = FontWeight.Medium,
                        modifier = Modifier
                            .background(
                                color = kindColor(memory.kind).copy(alpha = 0.1f),
                                shape = RoundedCornerShape(6.dp),
                            )
                            .padding(horizontal = 8.dp, vertical = 2.dp),
                    )

                    // Importance
                    if (memory.importance > 0.5) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                Icons.Filled.Favorite,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.tertiary,
                                modifier = Modifier.size(12.dp),
                            )
                            Spacer(Modifier.width(2.dp))
                            Text(
                                "${(memory.importance * 100).toInt()}%",
                                fontSize = 10.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }

                    // Date
                    if (memory.createdAt != null) {
                        Text(
                            text = memory.createdAt.take(10),
                            fontSize = 10.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f),
                        )
                    }
                }
            }

            // Delete button
            IconButton(
                onClick = { showDeleteConfirm = true },
                enabled = !isDeleting,
                modifier = Modifier.size(32.dp),
            ) {
                if (isDeleting) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(16.dp),
                        strokeWidth = 2.dp,
                    )
                } else {
                    Icon(
                        Icons.Filled.Delete,
                        contentDescription = "Esquecer",
                        tint = MaterialTheme.colorScheme.error.copy(alpha = 0.6f),
                        modifier = Modifier.size(18.dp),
                    )
                }
            }
        }
    }

    // Delete confirmation dialog
    if (showDeleteConfirm) {
        AlertDialog(
            onDismissRequest = { showDeleteConfirm = false },
            icon = {
                Icon(Icons.Filled.Delete, contentDescription = null, tint = MaterialTheme.colorScheme.error)
            },
            title = { Text("Esquecer esta memória?", fontWeight = FontWeight.Bold) },
            text = {
                Text(
                    "O kernel não terá mais acesso a este conhecimento.\n" +
                    "O conteúdo será removido permanentemente.",
                    fontSize = 14.sp,
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        showDeleteConfirm = false
                        onForget()
                    },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.error,
                    ),
                ) {
                    Text("Esquecer", color = MaterialTheme.colorScheme.onError)
                }
            },
            dismissButton = {
                TextButton(onClick = { showDeleteConfirm = false }) {
                    Text("Cancelar")
                }
            },
        )
    }
}

@Composable
private fun MemoryDetailView(
    memory: MemoryItem,
    onDismiss: () -> Unit,
    onForget: () -> Unit,
) {
    var showDeleteConfirm by remember { mutableStateOf(false) }

    LazyColumn(
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surface,
                ),
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    // Header with title and actions
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Box(
                            modifier = Modifier
                                .size(40.dp)
                                .background(
                                    color = kindColor(memory.kind).copy(alpha = 0.12f),
                                    shape = RoundedCornerShape(12.dp),
                                ),
                            contentAlignment = Alignment.Center,
                        ) {
                            Icon(
                                kindIcon(memory.kind),
                                contentDescription = null,
                                tint = kindColor(memory.kind),
                                modifier = Modifier.size(22.dp),
                            )
                        }

                        Spacer(Modifier.width(12.dp))

                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = memory.title ?: "Sem título",
                                fontSize = 18.sp,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onSurface,
                            )
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Text(
                                    text = memory.kind,
                                    fontSize = 12.sp,
                                    color = kindColor(memory.kind),
                                    fontWeight = FontWeight.Medium,
                                )
                                if (memory.createdAt != null) {
                                    Text(
                                        " · ${memory.createdAt.take(10)}",
                                        fontSize = 12.sp,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
                                }
                            }
                        }

                        Row {
                            IconButton(onClick = onDismiss) {
                                Icon(
                                    Icons.Filled.Close,
                                    contentDescription = "Fechar",
                                    tint = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                        }
                    }                        Divider(
                            modifier = Modifier.padding(vertical = 12.dp),
                            color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.08f),
                            thickness = 0.5.dp,
                        )

                        // Content
                        Text(
                            text = memory.content ?: "(sem conteúdo)",
                            fontSize = 14.sp,
                            color = MaterialTheme.colorScheme.onSurface,
                            lineHeight = 22.sp,
                        )

                        Divider(
                        modifier = Modifier.padding(vertical = 12.dp),
                        color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.08f),
                    )

                    // Metadata grid
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        MetaChip("Importância", "${(memory.importance * 100).toInt()}%")
                        MetaChip("Fonte", memory.source ?: "manual")
                        MetaChip("Tipo", memory.kind)
                    }

                    Spacer(Modifier.height(16.dp))

                    // Action buttons
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        OutlinedButton(
                            onClick = onDismiss,
                            modifier = Modifier.weight(1f),
                            shape = RoundedCornerShape(10.dp),
                        ) {
                            Text("Voltar", fontSize = 13.sp)
                        }

                        Button(
                            onClick = { showDeleteConfirm = true },
                            modifier = Modifier.weight(1f),
                            shape = RoundedCornerShape(10.dp),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = MaterialTheme.colorScheme.error,
                            ),
                        ) {
                            Icon(
                                Icons.Filled.Delete,
                                contentDescription = null,
                                modifier = Modifier.size(16.dp),
                            )
                            Spacer(Modifier.width(6.dp))
                            Text("Esquecer", fontSize = 13.sp)
                        }
                    }
                }
            }
        }

        item { Spacer(Modifier.height(16.dp)) }
    }

    // Delete confirmation dialog
    if (showDeleteConfirm) {
        AlertDialog(
            onDismissRequest = { showDeleteConfirm = false },
            icon = {
                Icon(Icons.Filled.Delete, contentDescription = null, tint = MaterialTheme.colorScheme.error)
            },
            title = { Text("Esquecer esta memória?", fontWeight = FontWeight.Bold) },
            text = {
                Text(
                    "Isso removerá permanentemente este conhecimento do kernel.",
                    fontSize = 14.sp,
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        showDeleteConfirm = false
                        onForget()
                        onDismiss()
                    },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.error,
                    ),
                ) {
                    Text("Esquecer", color = MaterialTheme.colorScheme.onError)
                }
            },
            dismissButton = {
                TextButton(onClick = { showDeleteConfirm = false }) {
                    Text("Cancelar")
                }
            },
        )
    }
}

// ═══════════════════════════════════════════════════════════
// Dialogs
// ═══════════════════════════════════════════════════════════

@Composable
private fun TeachMemoryDialog(
    onDismiss: () -> Unit,
    onTeach: (content: String, title: String?, kind: String) -> Unit,
    isTeaching: Boolean,
) {
    var content by remember { mutableStateOf("") }
    var title by remember { mutableStateOf("") }
    var kind by remember { mutableStateOf("fact") }

    val kinds = listOf("fact", "preference", "concept", "person", "project", "note")

    AlertDialog(
        onDismissRequest = { if (!isTeaching) onDismiss() },
        icon = {
            Icon(Icons.Filled.AutoAwesome, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
        },
        title = {
            Text("Ensinar ao kernel", fontWeight = FontWeight.Bold)
        },
        text = {
            Column {
                OutlinedTextField(
                    value = content,
                    onValueChange = { content = it },
                    label = { Text("Conteúdo *") },
                    placeholder = { Text("Ex: Meu aniversário é 15 de março") },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    minLines = 3,
                    maxLines = 6,
                )

                Spacer(Modifier.height(12.dp))

                OutlinedTextField(
                    value = title,
                    onValueChange = { title = it },
                    label = { Text("Título (opcional)") },
                    placeholder = { Text("Ex: Aniversário") },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    singleLine = true,
                )

                Spacer(Modifier.height(12.dp))

                Text("Tipo:", fontSize = 13.sp, fontWeight = FontWeight.Medium)
                Spacer(Modifier.height(6.dp))
                Row(
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    kinds.forEach { k ->
                        SuggestionChip(
                            onClick = { kind = k },
                            label = { Text(k, fontSize = 11.sp) },
                            selected = kind == k,
                            shape = RoundedCornerShape(20.dp),
                            colors = SuggestionChipDefaults.suggestionChipColors(
                                selectedContainerColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.15f),
                                selectedLabelColor = MaterialTheme.colorScheme.primary,
                            ),
                        )
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = { onTeach(content, title.takeIf { it.isNotBlank() }, kind) },
                enabled = content.isNotBlank() && !isTeaching,
            ) {
                if (isTeaching) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(16.dp),
                        strokeWidth = 2.dp,
                        color = MaterialTheme.colorScheme.onPrimary,
                    )
                } else {
                    Text("Ensinar")
                }
            }
        },
        dismissButton = {
            TextButton(
                onClick = onDismiss,
                enabled = !isTeaching,
            ) {
                Text("Cancelar")
            }
        },
    )
}

// ═══════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════

@Composable
private fun MetaChip(label: String, value: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            text = value,
            fontSize = 14.sp,
            fontWeight = FontWeight.SemiBold,
            color = MaterialTheme.colorScheme.primary,
        )
        Text(
            text = label,
            fontSize = 10.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f),
        )
    }
}

private fun kindColor(kind: String): Color {
    return when (kind.lowercase()) {
        "fact" -> Color(0xFF00BCD4)       // cyan
        "preference" -> Color(0xFFFF6D00)  // orange
        "concept" -> Color(0xFF7C4DFF)     // purple
        "person" -> Color(0xFF4CAF50)      // green
        "project" -> Color(0xFFE91E63)     // pink
        "note" -> Color(0xFF9E9E9E)        // grey
        else -> Color(0xFF00BCD4)          // cyan default
    }
}

private fun kindIcon(kind: String): ImageVector {
    return when (kind.lowercase()) {
        "fact" -> Icons.Filled.Lightbulb
        "preference" -> Icons.Filled.Favorite
        "concept" -> Icons.Filled.Bookmark
        "person" -> Icons.Filled.Bolt
        "project" -> Icons.Filled.AutoAwesome
        "note" -> Icons.Filled.ContentCopy
        else -> Icons.Filled.Lightbulb
    }
}
