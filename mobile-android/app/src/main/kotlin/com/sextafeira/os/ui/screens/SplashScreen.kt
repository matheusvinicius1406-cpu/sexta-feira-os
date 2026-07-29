package com.sextafeira.os.ui.screens

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.sextafeira.os.data.api.Session
import com.sextafeira.os.ui.navigation.Route
import kotlinx.coroutines.delay

@Composable
fun SplashScreen(navController: NavHostController) {
    var showLogo by remember { mutableStateOf(false) }
    val logoAlpha by animateFloatAsState(targetValue = if (showLogo) 1f else 0f)
    
    LaunchedEffect(Unit) {
        showLogo = true
        delay(1500)  // shorter delay — session was already loaded by SessionManager.init()
        
        val destination = if (Session.isAuthenticated) {
            Route.Dashboard.route
        } else {
            Route.Login.route
        }
        navController.navigate(destination) {
            popUpTo(Route.Splash.route) { inclusive = true }
        }
    }
    
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.alpha(logoAlpha)
        ) {
            Text(
                text = "SEXTA-FEIRA",
                fontSize = 48.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary
            )
            Text(
                text = "Personal AI Assistant",
                fontSize = 14.sp,
                color = MaterialTheme.colorScheme.secondary
            )
        }
    }
}
