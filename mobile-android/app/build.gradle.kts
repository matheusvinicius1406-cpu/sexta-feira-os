plugins {
    id("com.android.application")
    kotlin("android")
    kotlin("kapt")
    id("com.google.dagger.hilt.android")
    kotlin("plugin.serialization")
}

android {
    namespace = "com.sextafeira.os"
    compileSdk = rootProject.extra.get("compileSdk") as Int

    defaultConfig {
        applicationId = "com.sextafeira.os"
        minSdk = rootProject.extra.get("minSdk") as Int
        targetSdk = rootProject.extra.get("targetSdk") as Int
        versionCode = rootProject.extra.get("versionCode") as Int
        versionName = rootProject.extra.get("versionName") as String

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        vectorDrawables {
            useSupportLibrary = true
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
        debug {
            isMinifyEnabled = false
            debuggable = true
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
    }

    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.3"
    }

    packagingOptions {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

dependencies {
    // AndroidX Core
    implementation("androidx.core:core-ktx:${rootProject.extra.get("androidxCoreVersion")}")
    implementation("androidx.activity:activity-compose:${rootProject.extra.get("androidxActivityVersion")}")

    // Lifecycle
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:${rootProject.extra.get("androidxLifecycleVersion")}")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:${rootProject.extra.get("androidxLifecycleVersion")}")

    // Compose
    implementation("androidx.compose.ui:ui:${rootProject.extra.get("composeVersion")}")
    implementation("androidx.compose.ui:ui-graphics:${rootProject.extra.get("composeVersion")}")
    implementation("androidx.compose.material3:material3:${rootProject.extra.get("composeMaterialVersion")}")
    implementation("androidx.compose.runtime:runtime-livedata:${rootProject.extra.get("composeVersion")}")
    implementation("androidx.compose.ui:ui-tooling-preview:${rootProject.extra.get("composeVersion")}")
    debugImplementation("androidx.compose.ui:ui-tooling:${rootProject.extra.get("composeVersion")}")
    debugImplementation("androidx.compose.ui:ui-test-manifest:${rootProject.extra.get("composeVersion")}")

    // Navigation
    implementation("androidx.navigation:navigation-compose:2.6.0")

    // Networking - Retrofit + OkHttp
    implementation("com.squareup.retrofit2:retrofit:${rootProject.extra.get("retrofitVersion")}")
    implementation("com.squareup.okhttp3:okhttp:${rootProject.extra.get("okHttpVersion")}")
    implementation("com.squareup.okhttp3:logging-interceptor:${rootProject.extra.get("okHttpVersion")}")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:${rootProject.extra.get("kotlinSerializationVersion")}")
    implementation("com.jakewharton.retrofit:retrofit2-kotlinx-serialization-converter:1.0.0")

    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:${rootProject.extra.get("coroutinesVersion")}")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:${rootProject.extra.get("coroutinesVersion")}")

    // Database - Room
    implementation("androidx.room:room-runtime:${rootProject.extra.get("roomVersion")}")
    implementation("androidx.room:room-ktx:${rootProject.extra.get("roomVersion")}")
    kapt("androidx.room:room-compiler:${rootProject.extra.get("roomVersion")}")

    // Datastore (replaces SharedPreferences)
    implementation("androidx.datastore:datastore-preferences:1.0.0")

    // Hilt Dependency Injection
    implementation("com.google.dagger:hilt-android:${rootProject.extra.get("hiltVersion")}")
    kapt("com.google.dagger:hilt-compiler:${rootProject.extra.get("hiltVersion")}")

    // Compose with Hilt
    implementation("androidx.hilt:hilt-navigation-compose:1.0.0")

    // Logging
    implementation("com.jakewharton.timber:timber:5.0.1")

    // Testing
    testImplementation("junit:junit:${rootProject.extra.get("junitVersion")}")
    androidTestImplementation("androidx.test.ext:junit:${rootProject.extra.get("androidxTestVersion")}")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.5.1")
    androidTestImplementation("androidx.compose.ui:ui-test-junit4:${rootProject.extra.get("composeTestVersion")}")

    // Core module
    implementation(project(":core"))
}

kapt {
    correctErrorTypes = true
}
