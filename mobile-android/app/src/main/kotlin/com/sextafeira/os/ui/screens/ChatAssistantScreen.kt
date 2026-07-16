package com.sextafeira.os.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import androidx.compose.runtime.collectAsState
import com.sextafeira.os.viewmodel.ChatViewModel

@Composable
fun ChatAssistantScreen(
    navController: NavHostController,
    viewModel: ChatViewModel = remember { ChatViewModel() }
) {
    var messageInput by remember { mutableStateOf("") }
    var isListening by remember { mutableStateOf(false) }
    
    // Collect state from ViewModel
    val messages by viewModel.messages.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val error by viewModel.error.collectAsState()
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
    ) {
        // Header
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = { navController.popBackStack() }) {
                Icon(
                    Icons.Filled.ArrowBack,
                    contentDescription = "Back",
                    tint = MaterialTheme.colorScheme.primary
                )
            }
            Text(
                text = "Jarvis Assistant",
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary,
                modifier = Modifier.weight(1f)
            )
        }
        
        // Error Message
        if (error != null) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(MaterialTheme.colorScheme.error)
                    .padding(12.dp)
            ) {
                Text(
                    text = error!!,
                    color = MaterialTheme.colorScheme.onError,
                    fontSize = 12.sp,
                    modifier = Modifier
                        .align(Alignment.CenterStart)
                        .weight(1f)
                )
                Button(
                    onClick = { viewModel.clearError() },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.errorContainer
                    ),
                    modifier = Modifier.size(80.dp, 28.dp)
                ) {
                    Text("Dismiss", fontSize = 10.sp)
                }
            }
        }
        
        // Messages Area
        LazyColumn(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = androidx.compose.foundation.layout.Arrangement.spacedBy(12.dp),
            reverseLayout = false
        ) {
            items(messages) { message ->
                ChatMessageBubble(message)
            }
            
            // Loading indicator
            if (isLoading && messages.isNotEmpty()) {
                item {
                    Box(
                        modifier = Modifier
                            .align(Alignment.Start)
                            .background(
                                color = MaterialTheme.colorScheme.surfaceVariant,
                                shape = RoundedCornerShape(12.dp)
                            )
                            .padding(12.dp)
                    ) {
                        Text(
                            text = "⏳ Jarvis is thinking...",
                            color = MaterialTheme.colorScheme.onSurface,
                            fontSize = 14.sp
                        )
                    }
                }
            }
        }
        
        // Input Area
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            // Microphone Button
            Box(
                modifier = Modifier
                    .align(Alignment.CenterHorizontally)
                    .size(64.dp)
                    .background(
                        color = if (isListening) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary,
                        shape = CircleShape
                    ),
                contentAlignment = Alignment.Center
            ) {
                IconButton(
                    onClick = { isListening = !isListening },
                    modifier = Modifier.size(64.dp)
                ) {
                    Icon(
                        Icons.Filled.Mic,
                        contentDescription = "Microphone",
                        tint = MaterialTheme.colorScheme.onPrimary,
                        modifier = Modifier.size(32.dp)
                    )
                }
            }
            
            if (isListening) {
                Text(
                    text = "🎤 Listening...",
                    fontSize = 12.sp,
                    color = MaterialTheme.colorScheme.secondary,
                    modifier = Modifier
                        .align(Alignment.CenterHorizontally)
                        .padding(top = 8.dp)
                )
            }
            
            // Text Input
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 16.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                OutlinedTextField(
                    value = messageInput,
                    onValueChange = { messageInput = it },
                    label = { Text("Message Jarvis...") },
                    modifier = Modifier.weight(1f),
                    enabled = !isLoading
                )
                
                Button(
                    onClick = {
                        if (messageInput.isNotBlank() && !isLoading) {
                            viewModel.sendMessage(messageInput)
                            messageInput = ""
                        }
                    },
                    modifier = Modifier.padding(start = 8.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.primary
                    ),
                    enabled = messageInput.isNotBlank() && !isLoading
                ) {
                    Text("Send", fontSize = 12.sp)
                }
            }
        }
    }
}

@Composable
private fun ChatMessageBubble(message: com.sextafeira.os.domain.model.ChatMessage) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                color = if (message.isFromAssistant) 
                    MaterialTheme.colorScheme.surfaceVariant 
                else 
                    MaterialTheme.colorScheme.primary,
                shape = RoundedCornerShape(12.dp)
            )
            .align(if (message.isFromAssistant) Alignment.Start else Alignment.End)
            .fillMaxWidth(0.85f)
            .padding(12.dp)
    ) {
        Text(
            text = message.content,
            color = if (message.isFromAssistant) 
                MaterialTheme.colorScheme.onSurface 
            else 
                MaterialTheme.colorScheme.onPrimary,
            fontSize = 14.sp
        )
    }
}
