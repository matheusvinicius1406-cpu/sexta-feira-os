package com.sextafeira.os.ui.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.sextafeira.os.data.network.AuthEvent
import com.sextafeira.os.data.network.AuthEventBus
import com.sextafeira.os.data.session.SessionManager
import com.sextafeira.os.ui.screens.ChatAssistantScreen
import com.sextafeira.os.ui.screens.DashboardScreen
import com.sextafeira.os.ui.screens.LoginScreen
import com.sextafeira.os.ui.screens.MemoryCurationScreen
import com.sextafeira.os.ui.screens.SettingsScreen
import com.sextafeira.os.ui.screens.SplashScreen
import kotlinx.coroutines.flow.collectLatest

sealed class Route(val route: String) {
    object Splash : Route("splash")
    object Login : Route("login")
    object Dashboard : Route("dashboard")
    object Chat : Route("chat")
    object Settings : Route("settings")
    object MemoryCuration : Route("memory")
}

@Composable
fun RootNavigation() {
    val navController = rememberNavController()

    // Observe auth events and redirect to Login on 401.
    LaunchedEffect(Unit) {
        AuthEventBus.events.collectLatest { event ->
            when (event) {
                is AuthEvent.SessionExpired -> {
                    SessionManager.clear()
                    navController.navigate(Route.Login.route) {
                        popUpTo(0) { inclusive = true }
                    }
                }
            }
        }
    }

    NavHost(
        navController = navController,
        startDestination = Route.Splash.route
    ) {
        composable(Route.Splash.route) {
            SplashScreen(navController)
        }
        composable(Route.Login.route) {
            LoginScreen(navController)
        }
        composable(Route.Dashboard.route) {
            DashboardScreen(navController)
        }
        composable(Route.Chat.route) {
            ChatAssistantScreen(navController)
        }
        composable(Route.Settings.route) {
            SettingsScreen(navController)
        }
        composable(Route.MemoryCuration.route) {
            MemoryCurationScreen(navController)
        }
    }
}
