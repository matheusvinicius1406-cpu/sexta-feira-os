package com.sextafeira.os.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.Canvas
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
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Send
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.filled.VolumeUp
import androidx.compose.material.icons.filled.GraphicEq
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.core.content.ContextCompat
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.style.TextAlign
import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import androidx.compose.runtime.collectAsState
import com.sextafeira.os.viewmodel.ChatViewModel
import com.sextafeira.os.domain.model.ChatMessage
import kotlin.math.min
import kotlin.math.sqrt

@Composable
fun ChatAssistantScreen(
    navController: NavHostController,
    viewModel: ChatViewModel = hiltViewModel()
) {
    var messageInput by remember { mutableStateOf("") }
    var showPermissionDialog by remember { mutableStateOf(false) }
    val context = LocalContext.current

    // Runtime permission launcher for RECORD_AUDIO
    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (!granted) {
            showPermissionDialog = true
        }
    }

    // Permission check helper
    val hasMicPermission = ContextCompat.checkSelfPermission(
        context, Manifest.permission.RECORD_AUDIO
    ) == PackageManager.PERMISSION_GRANTED

    // Chat state
    val messages by viewModel.messages.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val streamingContent by viewModel.streamingContent.collectAsState()
    val streamingMessageId by viewModel.streamingMessageId.collectAsState()
    val error by viewModel.error.collectAsState()
    val voiceState by viewModel.voiceState.collectAsState()

    val listState = rememberLazyListState()

    // Auto-scroll to bottom
    LaunchedEffect(messages.size, streamingContent) {
        if (messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.size - 1)
        }
    }

    // Pulse animation for thinking/recording
    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
    val pulseAlpha by infiniteTransition.animateFloat(
        initialValue = 0.4f,
        targetValue = 1.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(600),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulse"
    )

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
    ) {
        // ── Header ───────────────────────────────────────
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 8.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = { navController.popBackStack() }) {
                Icon(
                    Icons.Filled.ArrowBack,
                    contentDescription = "Voltar",
                    tint = MaterialTheme.colorScheme.primary
                )
            }
            Text(
                text = "Jarvis",
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary,
                modifier = Modifier.weight(1f)
            )

            // TTS indicator
            if (voiceState.isPlaying) {
                SpeakingIndicator()
            }

            // Voice status
            if (voiceState.ttsAvailable) {
                Text(
                    "🔊",
                    fontSize = 14.sp,
                    modifier = Modifier.padding(end = 8.dp)
                )
            }
        }

        // ── Error ────────────────────────────────────────
        AnimatedVisibility(visible = error != null) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(MaterialTheme.colorScheme.error)
                    .padding(12.dp)
            ) {
                Text(
                    text = error ?: "",
                    color = MaterialTheme.colorScheme.onError,
                    fontSize = 12.sp,
                    modifier = Modifier.weight(1f)
                )
                Button(
                    onClick = { viewModel.clearError() },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.errorContainer
                    ),
                    modifier = Modifier.size(80.dp, 28.dp)
                ) {
                    Text("OK", fontSize = 10.sp)
                }
            }
        }

        // ── Recording Banner ─────────────────────────────
        AnimatedVisibility(
            visible = voiceState.isRecording,
            enter = fadeIn() + expandVertically(),
            exit = fadeOut() + shrinkVertically(),
        ) {
            RecordingBanner(amplitude = voiceState.amplitude, onStop = {
                viewModel.stopVoiceRecording(speakReply = voiceState.ttsAvailable)
            })
        }

        // ── Transcript Toast ─────────────────────────────
        AnimatedVisibility(
            visible = voiceState.transcript != null,
            enter = fadeIn() + expandVertically(),
            exit = fadeOut() + shrinkVertically(),
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(MaterialTheme.colorScheme.tertiaryContainer)
                    .padding(horizontal = 16.dp, vertical = 8.dp)
            ) {
                Text(
                    text = "🎤 ${voiceState.transcript ?: ""}",
                    color = MaterialTheme.colorScheme.onTertiaryContainer,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Medium,
                )
            }
        }

        // ── Messages Area ────────────────────────────────
        LazyColumn(
            state = listState,
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            items(messages, key = { it.id }) { message ->
                val isStreaming = streamingContent != null && streamingMessageId == message.id
                val cursor = if (isStreaming) " ▌" else ""
                ChatMessageBubble(
                    message = message.copy(content = message.content + cursor),
                    onSpeak = if (message.isFromAssistant && voiceState.ttsAvailable) {
                        { viewModel.speakText(message.content) }
                    } else null,
                )
            }

            // Loading indicator
            if (isLoading && streamingContent.isNullOrEmpty() && !voiceState.isRecording) {
                item {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 8.dp),
                        contentAlignment = Alignment.CenterStart
                    ) {
                        Box(
                            modifier = Modifier
                                .background(
                                    color = MaterialTheme.colorScheme.surfaceVariant,
                                    shape = RoundedCornerShape(16.dp)
                                )
                                .padding(horizontal = 16.dp, vertical = 10.dp)
                                .alpha(pulseAlpha)
                        ) {
                            Text(
                                text = "🤔 processando...",
                                color = MaterialTheme.colorScheme.onSurface,
                                fontSize = 14.sp,
                            )
                        }
                    }
                }
            }
        }

        // ── Input Area ───────────────────────────────────
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 8.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                // Microphone Button
                val micColor by animateColorAsState(
                    targetValue = if (voiceState.isRecording) MaterialTheme.colorScheme.error
                                 else MaterialTheme.colorScheme.primary,
                    animationSpec = tween(300),
                    label = "micColor",
                )

                Box(
                    modifier = Modifier
                        .size(48.dp)
                        .clip(CircleShape)
                        .background(micColor.copy(alpha = if (voiceState.isRecording) 0.2f else 0.15f))
                        .clickable {
                            if (voiceState.isRecording) {
                                viewModel.stopVoiceRecording(speakReply = voiceState.ttsAvailable)
                            } else if (hasMicPermission) {
                                viewModel.startVoiceRecording()
                            } else {
                                permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                            }
                        },
                    contentAlignment = Alignment.Center
                ) {
                    if (voiceState.isRecording) {
                        Icon(
                            Icons.Filled.Stop,
                            contentDescription = "Parar gravação",
                            tint = MaterialTheme.colorScheme.error,
                            modifier = Modifier.size(24.dp)
                        )
                    } else {
                        Icon(
                            Icons.Filled.Mic,
                            contentDescription = "Microfone",
                            tint = if (voiceState.sttAvailable) micColor
                                   else micColor.copy(alpha = 0.4f),
                            modifier = Modifier.size(24.dp)
                        )
                    }
                }

                // Text Input
                OutlinedTextField(
                    value = messageInput,
                    onValueChange = { messageInput = it },
                    placeholder = {
                        Text(
                            if (voiceState.sttAvailable) "Mensagem ou use o microfone..."
                            else "Mensagem para o Jarvis..."
                        )
                    },
                    modifier = Modifier.weight(1f),
                    enabled = !isLoading && !voiceState.isRecording,
                    shape = RoundedCornerShape(24.dp),
                    singleLine = true,
                )

                // Send Button
                Button(
                    onClick = {
                        if (messageInput.isNotBlank()) {
                            viewModel.sendMessage(messageInput)
                            messageInput = ""
                        }
                    },
                    modifier = Modifier.size(48.dp),
                    shape = CircleShape,
                    contentPadding = ButtonDefaults.TextButtonContentPadding,
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.primary
                    ),
                    enabled = messageInput.isNotBlank() && !isLoading && !voiceState.isRecording,
                ) {
                    Icon(
                        Icons.Filled.Send,
                        contentDescription = "Enviar",
                        tint = MaterialTheme.colorScheme.onPrimary,
                        modifier = Modifier.size(20.dp)
                    )
                }
            }
        }
    }

    // ── Permission Denied Dialog ────────────────────────
    if (showPermissionDialog) {
        AlertDialog(
            onDismissRequest = { showPermissionDialog = false },
            title = { Text("Permissão do Microfone", fontWeight = FontWeight.Bold) },
            text = {
                Text(
                    "O Sexta-Feira precisa de acesso ao microfone para capturar " +
                    "comandos de voz. Conceda a permissão nas Configurações do sistema.",
                    fontSize = 14.sp,
                )
            },
            confirmButton = {
                TextButton(onClick = { showPermissionDialog = false }) {
                    Text("Entendi")
                }
            },
        )
    }
}

// ═══════════════════════════════════════════════════════════
// Recording Banner (shown during voice recording)
// ═══════════════════════════════════════════════════════════

@Composable
private fun RecordingBanner(
    amplitude: Int,
    onStop: () -> Unit,
) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.error.copy(alpha = 0.08f))
            .padding(horizontal = 16.dp, vertical = 12.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            // Recording dot animation
            Box(
                modifier = Modifier
                    .size(12.dp)
                    .background(Color.Red, CircleShape)
            )

            Spacer(Modifier.width(12.dp))

            // Amplitude visualizer
            VoiceWaveform(amplitude = amplitude, modifier = Modifier.weight(1f).height(32.dp))

            Spacer(Modifier.width(12.dp))

            Text(
                "Gravando",
                color = MaterialTheme.colorScheme.error,
                fontSize = 13.sp,
                fontWeight = FontWeight.SemiBold,
            )

            Spacer(Modifier.width(8.dp))

            // Stop button
            Button(
                onClick = onStop,
                modifier = Modifier.size(36.dp),
                shape = CircleShape,
                contentPadding = ButtonDefaults.TextButtonContentPadding,
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.error,
                ),
            ) {
                Icon(
                    Icons.Filled.Stop,
                    contentDescription = "Parar",
                    tint = MaterialTheme.colorScheme.onError,
                    modifier = Modifier.size(18.dp)
                )
            }
        }
    }
}

// ═══════════════════════════════════════════════════════════
// Voice Waveform (amplitude visualizer)
// ═══════════════════════════════════════════════════════════

@Composable
private fun VoiceWaveform(
    amplitude: Int,
    modifier: Modifier = Modifier,
) {
    val normalizedAmplitude = remember(amplitude) {
        min(amplitude / 32767f, 1f)
    }

    val barCount = 30
    val amplitudes = remember(barCount) { FloatArray(barCount) { 0f } }

    // Shift amplitudes
    for (i in 0 until barCount - 1) {
        amplitudes[i] = amplitudes[i + 1]
    }
    amplitudes[barCount - 1] = normalizedAmplitude

    Canvas(modifier = modifier) {
        val barWidth = size.width / barCount
        val centerY = size.height / 2f

        for (i in 0 until barCount) {
            val amp = amplitudes[i].coerceAtLeast(0.02f)
            val barHeight = amp * size.height * 0.9f
            val x = i * barWidth + barWidth * 0.2f
            val actualBarWidth = barWidth * 0.6f

            drawRoundRect(
                color = MaterialTheme.colorScheme.error.copy(
                    alpha = 0.5f + amp * 0.5f
                ),
                topLeft = Offset(x, centerY - barHeight / 2f),
                size = androidx.compose.ui.geometry.Size(actualBarWidth, barHeight),
                cornerRadius = androidx.compose.ui.geometry.CornerRadius(2f, 2f),
            )
        }
    }
}

// ═══════════════════════════════════════════════════════════
// Speaking Indicator (animated TTS indicator)
// ═══════════════════════════════════════════════════════════

@Composable
private fun SpeakingIndicator() {
    val infiniteTransition = rememberInfiniteTransition(label = "speaking")

    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.padding(end = 8.dp)
    ) {
        Icon(
            Icons.Filled.VolumeUp,
            contentDescription = "Falando",
            tint = MaterialTheme.colorScheme.primary,
            modifier = Modifier.size(18.dp)
        )
        Spacer(Modifier.width(4.dp))

        repeat(3) { index ->
            val height by infiniteTransition.animateFloat(
                initialValue = 4f,
                targetValue = 16f,
                animationSpec = infiniteRepeatable(
                    animation = tween(
                        durationMillis = 400,
                        delayMillis = index * 120,
                        easing = LinearEasing,
                    ),
                    repeatMode = RepeatMode.Reverse,
                ),
                label = "bar$index",
            )
            Box(
                modifier = Modifier
                    .width(3.dp)
                    .height(height.dp)
                    .padding(horizontal = 1.dp)
                    .background(
                        color = MaterialTheme.colorScheme.primary,
                        shape = RoundedCornerShape(2.dp),
                    )
            )
        }
    }
}

// ═══════════════════════════════════════════════════════════
// Chat Message Bubble
// ═══════════════════════════════════════════════════════════

@Composable
private fun ChatMessageBubble(
    message: ChatMessage,
    onSpeak: (() -> Unit)? = null,
) {
    Box(
        modifier = Modifier.fillMaxWidth(),
        contentAlignment = if (message.isFromAssistant) Alignment.TopStart else Alignment.TopEnd
    ) {
        Column(
            horizontalAlignment = if (message.isFromAssistant) Alignment.Start else Alignment.End,
            modifier = Modifier.fillMaxWidth(0.88f)
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(
                        color = if (message.isFromAssistant)
                            MaterialTheme.colorScheme.surfaceVariant
                        else
                            MaterialTheme.colorScheme.primary,
                        shape = RoundedCornerShape(
                            topStart = 16.dp,
                            topEnd = 16.dp,
                            bottomStart = if (message.isFromAssistant) 4.dp else 16.dp,
                            bottomEnd = if (message.isFromAssistant) 16.dp else 4.dp,
                        )
                    )
                    .padding(horizontal = 14.dp, vertical = 10.dp)
            ) {
                Text(
                    text = message.content,
                    color = if (message.isFromAssistant)
                        MaterialTheme.colorScheme.onSurface
                    else
                        MaterialTheme.colorScheme.onPrimary,
                    fontSize = 15.sp,
                    lineHeight = 22.sp,
                )
            }

            // TTS speak button for assistant messages
            if (message.isFromAssistant && onSpeak != null && message.content.isNotBlank()) {
                IconButton(
                    onClick = onSpeak,
                    modifier = Modifier.size(28.dp)
                ) {
                    Icon(
                        Icons.Filled.VolumeUp,
                        contentDescription = "Ouvir",
                        tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f),
                        modifier = Modifier.size(16.dp)
                    )
                }
            }
        }
    }
}
