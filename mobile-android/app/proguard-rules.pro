# Proguard rules for Sexta-Feira OS
#
# Strategy: obfuscate EVERYTHING except what needs reflection at runtime.
# R8 keeps manifest-declared components (MainActivity, AgentService) and
# anything referenced by kept code automatically; the keeps below are only
# for the pieces that would break if renamed/stripped.

# --- Compose (bundled consumer rules + explicit keep for safety) ---
-keep class androidx.compose.** { *; }
-keepclasseswithmembernames class androidx.compose.** { *; }

# --- Retrofit + OkHttp ---
-keep class retrofit2.** { *; }
-keepclasseswithmembers class * {
    @retrofit2.http.* <methods>;
}
-keep class okhttp3.** { *; }
-keepclasseswithmembers class okhttp3.** { *; }

# --- Hilt / Dagger (generated code is wired by name via its own consumer rules) ---
-keep class dagger.hilt.** { *; }
-keep class com.google.dagger.** { *; }

# --- Gson: model classes are read reflectively by field name ---
-keep class com.sextafeira.os.data.api.** { *; }
-keep class com.sextafeira.os.data.agent.** { *; }
-keepclassmembers class * {
    @com.google.gson.annotations.SerializedName <fields>;
}

# --- Core module (shared code, no reflection, but small — keep for stability) ---
-keep class com.sextafeira.os.core.** { *; }

# --- Kotlin metadata ---
-keep class kotlin.metadata.** { *; }
-keepclassmembers class * {
    *** synthesizeObject(...);
}

# Line numbers for debugging release crashes (names are still obfuscated)
-keepattributes SourceFile,LineNumberTable
-renamesourcefileattribute SourceFile
