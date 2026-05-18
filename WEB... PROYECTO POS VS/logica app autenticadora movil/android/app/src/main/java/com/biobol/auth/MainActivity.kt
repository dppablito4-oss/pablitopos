package com.biobol.auth

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import com.biobol.auth.ui.AdminAuthViewModel
import com.biobol.auth.ui.AdminRecoveryScreen
import com.biobol.auth.ui.theme.BiobolTheme

class MainActivity : ComponentActivity() {
    private val vm: AdminAuthViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            BiobolTheme {
                AdminRecoveryScreen(vm)
            }
        }
    }
}
