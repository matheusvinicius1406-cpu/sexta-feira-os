package com.sextafeira.os

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import com.sextafeira.os.data.agent.AgentSession
import com.sextafeira.os.data.session.SessionManager
import com.sextafeira.os.ui.navigation.RootNavigation
import com.sextafeira.os.ui.theme.SextaFeiraTheme
import dagger.hilt.android.AndroidEntryPoint
import timber.log.Timber

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        if (BuildConfig.DEBUG) {
            Timber.plant(Timber.DebugTree())
        }
        
        // Restore saved session from DataStore before the UI renders,
        // so SplashScreen can check Session.isAuthenticated immediately.
        SessionManager.init(applicationContext)
        // Restore device pairing so the agent knows it is a body.
        AgentSession.init(applicationContext)
        
        setContent {
            SextaFeiraTheme {
                Surface(
                    modifier = Modifier.fillMaxSize()
                ) {
                    RootNavigation()
                }
            }
        }
    }
}
