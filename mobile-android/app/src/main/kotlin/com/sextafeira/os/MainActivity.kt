package com.sextafeira.os

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
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
