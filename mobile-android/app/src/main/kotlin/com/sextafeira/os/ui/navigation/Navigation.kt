package com.sextafeira.os.ui.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.sextafeira.os.ui.screens.SplashScreen
import com.sextafeira.os.ui.screens.LoginScreen
import com.sextafeira.os.ui.screens.DashboardScreen
import com.sextafeira.os.ui.screens.ChatAssistantScreen
import com.sextafeira.os.ui.screens.SettingsScreen

sealed class Route(val route: String) {
    object Splash : Route("splash")
    object Login : Route("login")
    object Dashboard : Route("dashboard")
    object Chat : Route("chat")
    object Settings : Route("settings")
}

@Composable
fun RootNavigation() {
    val navController = rememberNavController()
    
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
    }
}
