import java.util.Properties

plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

/* 🔴 **릴리스 서명 값은 저장소 밖에 둔다** (2026-09-29). 이 저장소는 공개라
   키스토어 경로·비밀번호를 여기 적으면 그대로 인터넷에 올라간다 —
   `android/key.properties` 와 `*.jks` 는 `.gitignore` 에 있다.

   🔴 **없어도 빌드가 죽지 않는다.** 이 파일이 없는 사람(CI·새로 받은 사람)은
   아래에서 `release` 가 디버그 키로 서명된다 — 예전 그대로다. 없다고 터지게
   만들면 서명할 일이 없는 사람까지 키스토어를 만들어야 한다.

   ⚠️ **디버그 키로 서명된 릴리스는 구글 로그인이 안 된다** — 콘솔에 등록된
   SHA-1 과 안 맞는다. 남에게 줄 APK 는 반드시 이 파일이 있는 자리에서 굽는다. */
val keystoreProperties = Properties().apply {
    val f = rootProject.file("key.properties")
    if (f.exists()) f.inputStream().use { load(it) }
}
val hasReleaseKey = keystoreProperties.getProperty("storeFile") != null

android {
    namespace = "cloud.supersub.super_sub"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        // TODO: Specify your own unique Application ID (https://developer.android.com/studio/build/application-id.html).
        applicationId = "cloud.supersub.super_sub"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    signingConfigs {
        if (hasReleaseKey) {
            create("release") {
                storeFile = file(keystoreProperties.getProperty("storeFile"))
                storePassword = keystoreProperties.getProperty("storePassword")
                keyAlias = keystoreProperties.getProperty("keyAlias")
                keyPassword = keystoreProperties.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            /* 🔴 **키가 있으면 진짜 키로, 없으면 디버그 키로.** 머리말 참고 —
               없다고 빌드를 죽이지 않는다. ⚠️ 디버그 키로 서명되면 구글
               로그인이 **안 된다**(SHA-1 불일치). */
            signingConfig = if (hasReleaseKey) {
                signingConfigs.getByName("release")
            } else {
                signingConfigs.getByName("debug")
            }
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}
