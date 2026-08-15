plugins {
    application
    id("java")
}

group = "os.sextafeira"
version = "0.1.0"

repositories {
    mavenCentral()
}

dependencies {
    implementation("io.javalin:javalin:6.3.0")
    implementation("com.fasterxml.jackson.core:jackson-databind:2.17.2")
    implementation("org.slf4j:slf4j-simple:2.0.13")

    testImplementation("org.junit.jupiter:junit-jupiter:5.10.2")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(17)
    }
}

application {
    mainClass = "os.sextafeira.jarvis.Main"
}

tasks.test {
    useJUnitPlatform()
    testLogging {
        showStandardStreams = true
    }
}
