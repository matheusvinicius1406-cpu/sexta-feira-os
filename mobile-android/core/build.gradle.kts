plugins {
    id("com.android.library")
    kotlin("android")
}

android {
    namespace = "com.sextafeira.os.core"
    compileSdk = rootProject.extra.get("compileSdk") as Int

    defaultConfig {
        minSdk = rootProject.extra.get("minSdk") as Int
        targetSdk = rootProject.extra.get("targetSdk") as Int
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:${rootProject.extra.get("androidxCoreVersion")}")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:${rootProject.extra.get("coroutinesVersion")}")
    
    // Logging
    implementation("com.jakewharton.timber:timber:5.0.1")
    
    testImplementation("junit:junit:${rootProject.extra.get("junitVersion")}")
}
