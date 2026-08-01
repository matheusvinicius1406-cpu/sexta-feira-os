@file:OptIn(ExperimentalMaterial3Api::class)

package com.sextafeira.os.ui.screens

import androidx.compose.animation.AnimatedVisibility
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Devices
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.Memory
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Radar
import androidx.compose.material.icons.filled.Sensors
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material.icons.filled.Wifi
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Divider
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
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
import com.sextafeira.os.data.api.DeviceInfo
import com.sextafeira.os.ui.navigation.Route
import com.sextafeira.os.viewmodel.ConnectionStatus
import com.sextafeira.os.viewmodel.SettingsViewModel

@Composable
fun SettingsScreen(
    navController: NavHostController,
    viewModel: SettingsViewModel = hiltViewModel(),
) {
    val uiState by viewModel.uiState.collectAsState()

    // Load devices when screen appears
    LaunchedEffect(Unit) {
        viewModel.loadDevices()
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
    ) {
        // ── Top App Bar ───────────────────────────────────
        TopAppBar(
            title = {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        Icons.Filled.Settings,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(24.dp)
                    )
                    Spacer(Modifier.width(10.dp))
                    Text(
                        "Configurações",
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

        // ── Scrollable Content ────────────────────────────
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            // Server Connection Section
            item { ServerConnectionSection(uiState, viewModel) }

            // Device Pairing Section
            item { DevicePairingSection(uiState, viewModel) }

            // Paired Devices Section
            item { PairedDevicesSection(uiState, viewModel) }

            // Memory Curation (shortcut)
            item { MemoryShortcutSection(navController) }

            // Feature Toggles Section
            item { FeatureTogglesSection(uiState, viewModel) }

            // About Section
            item { AboutSection() }

            // Bottom spacer
            item { Spacer(Modifier.height(24.dp)) }
        }
    }
}

// ═══════════════════════════════════════════════════════════
// Sections
// ═══════════════════════════════════════════════════════════

@Composable
private fun ServerConnectionSection(
    uiState: com.sextafeira.os.viewmodel.SettingsUiState,
    viewModel: SettingsViewModel,
) {
    SectionCard(
        icon = Icons.Filled.Wifi,
        title = "Conexão com o Kernel",
        subtitle = "Endereço do servidor Sexta-Feira OS",
    ) {
        // URL Input
        OutlinedTextField(
            value = uiState.kernelUrl,
            onValueChange = { viewModel.onKernelUrlChanged(it) },
            label = { Text("URL do Kernel") },
            placeholder = { Text("http://192.168.0.10:8000") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp),
            supportingText = {
                Text(
                    "Para LAN use o IP do servidor. Para Termux use 127.0.0.1",
                    fontSize = 11.sp,
                )
            },
        )

        Spacer(Modifier.height(12.dp))

        // Status Indicator + Action Buttons
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            // Connection Status Badge
            ConnectionStatusBadge(uiState.connectionStatus)

            Spacer(Modifier.weight(1f))

            // Test Connection Button
            Button(
                onClick = { viewModel.testConnection(saveOnSuccess = true) },
                enabled = !uiState.isTestingConnection && uiState.kernelUrl.isNotBlank(),
                modifier = Modifier.height(40.dp),
                shape = RoundedCornerShape(10.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                ),
            ) {
                if (uiState.isTestingConnection) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(16.dp),
                        color = MaterialTheme.colorScheme.onPrimary,
                        strokeWidth = 2.dp,
                    )
                } else {
                    Icon(Icons.Filled.Radar, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("Testar", fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                }
            }
        }

        // Connection Error
        AnimatedVisibility(
            visible = uiState.connectionError != null,
            enter = fadeIn() + expandVertically(),
            exit = fadeOut() + shrinkVertically(),
        ) {
            Text(
                text = uiState.connectionError ?: "",
                color = MaterialTheme.colorScheme.error,
                fontSize = 12.sp,
                modifier = Modifier.padding(top = 8.dp),
            )
        }
    }
}

@Composable
private fun MemoryShortcutSection(navController: NavHostController) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { navController.navigate(Route.MemoryCuration.route) },
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface,
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .background(
                        color = MaterialTheme.colorScheme.primary.copy(alpha = 0.12f),
                        shape = RoundedCornerShape(12.dp),
                    ),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    Icons.Filled.AutoAwesome,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(22.dp),
                )
            }
            Spacer(Modifier.width(14.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    "Curadoria de Memória",
                    fontSize = 15.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSurface,
                )
                Text(
                    "Ver, buscar, ensinar e esquecer o que o kernel sabe sobre você",
                    fontSize = 11.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            Icon(
                Icons.Filled.ChevronRight,
                contentDescription = "Abrir",
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.size(20.dp),
            )
        }
    }
}

@Composable
private fun DevicePairingSection(
    uiState: com.sextafeira.os.viewmodel.SettingsUiState,
    viewModel: SettingsViewModel,
) {
    SectionCard(
        icon = Icons.Filled.Link,
        title = "Pareamento de Dispositivos",
        subtitle = "Um cérebro, muitos corpos",
    ) {
        OutlinedTextField(
            value = uiState.pairingCode,
            onValueChange = { viewModel.onPairingCodeChanged(it) },
            label = { Text("Código de Pareamento") },
            placeholder = { Text("Insira o código do .env") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp),
            supportingText = {
                Text(
                    "Configure DEVICE_PAIRING_CODE no .env do servidor",
                    fontSize = 11.sp,
                )
            },
        )

        Spacer(Modifier.height(12.dp))

        Button(
            onClick = { viewModel.pairDevice() },
            enabled = !uiState.isPairing && uiState.pairingCode.isNotBlank(),
            modifier = Modifier.fillMaxWidth().height(44.dp),
            shape = RoundedCornerShape(12.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = MaterialTheme.colorScheme.secondary,
            ),
        ) {
            if (uiState.isPairing) {
                CircularProgressIndicator(
                    modifier = Modifier.size(18.dp),
                    color = MaterialTheme.colorScheme.onSecondary,
                    strokeWidth = 2.dp,
                )
                Spacer(Modifier.width(8.dp))
                Text("Pareando...", fontSize = 14.sp)
            } else {
                Icon(Icons.Filled.PhoneAndroid, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(8.dp))
                Text("Parear Dispositivo", fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
            }
        }

        // Pairing Messages
        AnimatedVisibility(visible = uiState.pairingError != null) {
            Text(
                text = uiState.pairingError ?: "",
                color = MaterialTheme.colorScheme.error,
                fontSize = 12.sp,
                modifier = Modifier.padding(top = 8.dp),
            )
        }

        AnimatedVisibility(visible = uiState.pairingSuccess != null) {
            Text(
                text = uiState.pairingSuccess ?: "",
                color = MaterialTheme.colorScheme.tertiary,
                fontSize = 12.sp,
                fontWeight = FontWeight.SemiBold,
                modifier = Modifier.padding(top = 8.dp),
            )
        }
    }
}

@Composable
private fun PairedDevicesSection(
    uiState: com.sextafeira.os.viewmodel.SettingsUiState,
    viewModel: SettingsViewModel,
) {
    SectionCard(
        icon = Icons.Filled.Devices,
        title = "Dispositivos Pareados",
        subtitle = if (uiState.devices.size == 1) "1 dispositivo"
                   else "${uiState.devices.size} dispositivos",
    ) {
        if (uiState.isLoadingDevices) {
            Box(
                modifier = Modifier.fillMaxWidth().padding(16.dp),
                contentAlignment = Alignment.Center,
            ) {
                CircularProgressIndicator(
                    modifier = Modifier.size(24.dp),
                    strokeWidth = 2.dp,
                )
            }
        } else if (uiState.devices.isEmpty()) {
            Box(
                modifier = Modifier.fillMaxWidth().padding(vertical = 16.dp),
                contentAlignment = Alignment.Center,
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(
                        Icons.Filled.Sensors,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.4f),
                        modifier = Modifier.size(40.dp),
                    )
                    Spacer(Modifier.height(8.dp))
                    Text(
                        "Nenhum dispositivo pareado",
                        color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f),
                        fontSize = 14.sp,
                    )
                    Text(
                        "Use o código de pareamento acima",
                        color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.4f),
                        fontSize = 12.sp,
                    )
                }
            }
        } else {
            uiState.devices.forEach { device ->
                DeviceItem(device = device, onRevoke = { viewModel.revokeDevice(device.id) })
            }
        }

        // Device Error
        AnimatedVisibility(visible = uiState.deviceError != null) {
            Text(
                text = uiState.deviceError ?: "",
                color = MaterialTheme.colorScheme.error,
                fontSize = 12.sp,
                modifier = Modifier.padding(top = 4.dp),
            )
        }
    }
}

@Composable
private fun FeatureTogglesSection(
    uiState: com.sextafeira.os.viewmodel.SettingsUiState,
    viewModel: SettingsViewModel,
) {
    SectionCard(
        icon = Icons.Filled.Memory,
        title = "Funcionalidades",
        subtitle = "Ativar ou desativar módulos do kernel",
    ) {
        ToggleItem(
            icon = Icons.Filled.Mic,
            title = "Entrada de Voz",
            description = "Comandos de voz ativos",
            checked = uiState.voiceEnabled,
            onCheckChange = { viewModel.onVoiceEnabledChanged(it) },
        )
        Divider(modifier = Modifier.padding(vertical = 2.dp), color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.08f), thickness = 0.5.dp)
        ToggleItem(
            icon = Icons.Filled.Sync,
            title = "Sistema de Memória",
            description = "Histórico e aprendizado contínuo",
            checked = uiState.memoryEnabled,
            onCheckChange = { viewModel.onMemoryEnabledChanged(it) },
        )
        Divider(modifier = Modifier.padding(vertical = 2.dp), color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.08f), thickness = 0.5.dp)
        ToggleItem(
            icon = Icons.Filled.PlayArrow,
            title = "Automações",
            description = "Tarefas automáticas (Teia)",
            checked = uiState.automationEnabled,
            onCheckChange = { viewModel.onAutomationEnabledChanged(it) },
        )
    }
}

@Composable
private fun AboutSection() {
    SectionCard(
        icon = Icons.Filled.Info,
        title = "Sobre",
        subtitle = "Sexta-Feira OS",
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text("Versão", fontSize = 14.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(
                "0.1.0",
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.primary,
                fontFamily = FontFamily.Monospace,
            )
        }
        Spacer(Modifier.height(6.dp))
        Row(
            modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text("Modo", fontSize = 14.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(
                "100% Local / Privado",
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.tertiary,
            )
        }
        Spacer(Modifier.height(6.dp))
        Row(
            modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text("Modelo", fontSize = 14.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(
                "Ollama (local)",
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.secondary,
            )
        }
    }
}

// ═══════════════════════════════════════════════════════════
// Reusable Components
// ═══════════════════════════════════════════════════════════

@Composable
private fun SectionCard(
    icon: ImageVector,
    title: String,
    subtitle: String,
    content: @Composable () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface,
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            // Header
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .background(
                            color = MaterialTheme.colorScheme.primary.copy(alpha = 0.12f),
                            shape = RoundedCornerShape(10.dp),
                        ),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(
                        icon,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(20.dp),
                    )
                }
                Spacer(Modifier.width(12.dp))
                Column {
                    Text(
                        title,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurface,
                    )
                    Text(
                        subtitle,
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }

            Spacer(Modifier.height(16.dp))

            // Content
            content()
        }
    }
}

@Composable
private fun ConnectionStatusBadge(status: ConnectionStatus) {
    val (color, label) = when (status) {
        ConnectionStatus.UNKNOWN -> MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.4f) to "Não testado"
        ConnectionStatus.CHECKING -> MaterialTheme.colorScheme.secondary to "Testando..."
        ConnectionStatus.ONLINE -> Color(0xFF4CAF50) to "Online"
        ConnectionStatus.OFFLINE -> MaterialTheme.colorScheme.error to "Offline"
    }

    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(
            modifier = Modifier
                .size(10.dp)
                .clip(CircleShape)
                .background(color)
        )
        Spacer(Modifier.width(8.dp))
        Text(label, fontSize = 13.sp, color = color, fontWeight = FontWeight.Medium)
    }
}

@Composable
private fun DeviceItem(
    device: DeviceInfo,
    onRevoke: () -> Unit,
) {
    var showRevokeConfirm by remember { mutableStateOf(false) }

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        // Device icon based on kind
        Box(
            modifier = Modifier
                .size(36.dp)
                .background(
                    color = if (device.revoked) MaterialTheme.colorScheme.error.copy(alpha = 0.1f)
                            else MaterialTheme.colorScheme.primary.copy(alpha = 0.1f),
                    shape = RoundedCornerShape(10.dp),
                ),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                imageVector = when (device.kind.lowercase()) {
                    "phone" -> Icons.Filled.PhoneAndroid
                    "car" -> Icons.Filled.Sensors
                    else -> Icons.Filled.Devices
                },
                contentDescription = null,
                tint = if (device.revoked) MaterialTheme.colorScheme.error
                       else MaterialTheme.colorScheme.primary,
                modifier = Modifier.size(20.dp),
            )
        }

        Spacer(Modifier.width(12.dp))

        Column(modifier = Modifier.weight(1f)) {
            Text(
                device.name,
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
                color = if (device.revoked) MaterialTheme.colorScheme.onSurfaceVariant
                        else MaterialTheme.colorScheme.onSurface,
            )
            Text(
                "${device.kind} · ${device.pairedAt?.take(10) ?: "desconhecido"}",
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f),
            )
        }

        if (!device.revoked) {
            IconButton(
                onClick = { showRevokeConfirm = true },
                modifier = Modifier.size(36.dp),
            ) {
                Icon(
                    Icons.Filled.Close,
                    contentDescription = "Revogar",
                    tint = MaterialTheme.colorScheme.error.copy(alpha = 0.7f),
                    modifier = Modifier.size(18.dp),
                )
            }
        } else {
            Text(
                "Revogado",
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.error,
                fontWeight = FontWeight.Medium,
            )
        }
    }

    // Revoke confirmation dialog
    if (showRevokeConfirm) {
        androidx.compose.material3.AlertDialog(
            onDismissRequest = { showRevokeConfirm = false },
            icon = {
                Icon(Icons.Filled.Delete, contentDescription = null, tint = MaterialTheme.colorScheme.error)
            },
            title = {
                Text("Revogar dispositivo?", fontWeight = FontWeight.Bold)
            },
            text = {
                Text(
                    "O dispositivo \"${device.name}\" perderá acesso ao kernel.\n" +
                    "Você precisará pareá-lo novamente para reconectar.",
                    fontSize = 14.sp,
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        showRevokeConfirm = false
                        onRevoke()
                    },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.error,
                    ),
                ) {
                    Text("Revogar", color = MaterialTheme.colorScheme.onError)
                }
            },
            dismissButton = {
                TextButton(onClick = { showRevokeConfirm = false }) {
                    Text("Cancelar")
                }
            },
        )
    }
}

@Composable
private fun ToggleItem(
    icon: ImageVector,
    title: String,
    description: String,
    checked: Boolean,
    onCheckChange: (Boolean) -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(
            icon,
            contentDescription = null,
            tint = if (checked) MaterialTheme.colorScheme.primary
                   else MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f),
            modifier = Modifier.size(22.dp),
        )
        Spacer(Modifier.width(12.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(
                title,
                fontSize = 14.sp,
                fontWeight = FontWeight.Medium,
                color = MaterialTheme.colorScheme.onSurface,
            )
            Text(
                description,
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Switch(
            checked = checked,
            onCheckedChange = onCheckChange,
            colors = SwitchDefaults.colors(
                checkedThumbColor = MaterialTheme.colorScheme.primary,
                checkedTrackColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.3f),
            ),
        )
    }
}
