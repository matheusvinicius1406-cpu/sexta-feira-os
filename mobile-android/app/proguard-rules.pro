# Proguard rules for Sexta-Feira OS

# Keep Compose
-keep class androidx.compose.** { *; }
-keepclasseswithmembernames class androidx.compose.** { *; }

# Keep Retrofit
-keep class retrofit2.** { *; }
-keepclasseswithmembers class * {
    @retrofit2.http.* <methods>;
}

# Keep OkHttp
-keep class okhttp3.** { *; }
-keepclasseswithmembers class okhttp3.** { *; }

# Keep Hilt
-keep class dagger.hilt.** { *; }
-keep class com.google.dagger.** { *; }

# Keep model classes
-keep class com.sextafeira.os.data.api.** { *; }
-keep class com.sextafeira.os.domain.model.** { *; }

# Keep Kotlin metadata
-keep class kotlin.metadata.** { *; }
-keepclassmembers class * {
    *** synthesizeObject(...);
}

# Keep our app code
-keep class com.sextafeira.os.** { *; }

# Preserve line numbers for debugging
-keepattributes SourceFile,LineNumberTable
-renamesourcefileattribute SourceFile
