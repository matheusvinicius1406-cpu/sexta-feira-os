plugins {
    id("com.android.application") version "8.1.0" apply false
    id("com.android.library") version "8.1.0" apply false
    kotlin("android") version "1.9.0" apply false
    kotlin("jvm") version "1.9.0" apply false
}

tasks.register("clean", Delete::class) {
    delete(rootProject.buildDir)
}

// Version catalog for dependencies
extra.apply {
    set("compileSdk", 34)
    set("minSdk", 24)
    set("targetSdk", 34)
    set("versionCode", 1)
    set("versionName", "0.1.0")

    // Kotlin
    set("kotlinVersion", "1.9.0")
    set("coroutinesVersion", "1.7.2")

    // Android
    set("androidGradlePlugin", "8.1.0")
    set("androidxCoreVersion", "1.10.1")
    set("androidxLifecycleVersion", "2.6.1")
    set("androidxActivityVersion", "1.7.2")
    set("composeVersion", "1.5.1")
    set("composeMaterialVersion", "1.1.1")
    set("composeCompilerExtensionVersion", "1.5.3")

    // Networking
    set("okHttpVersion", "4.11.0")
    set("retrofitVersion", "2.9.0")
    set("kotlinSerializationVersion", "1.5.1")

    // Database
    set("roomVersion", "2.5.2")

    // Dependency Injection
    set("hiltVersion", "2.47")

    // Testing
    set("junitVersion", "4.13.2")
    set("androidxTestVersion", "1.5.2")
    set("composeTestVersion", "1.5.1")
}
