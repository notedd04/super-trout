# Build and release

## Android debug APK

```bash
cd android
./gradlew assembleDebug
```

Configure `ANDROID_HOME` or `android/local.properties` to an SDK containing API 35 and build-tools 35.0.0.

## Release APK

No signing key is committed. Configure a JKS in GitHub Actions secrets or Android Studio. The workflow currently publishes debug and unsigned release artifacts for review.

## Checksums

Generate local checksums:

```bash
sha256sum android/app/build/outputs/apk/debug/app-debug.apk \
  android/app/build/outputs/apk/release/app-release-unsigned.apk
```

## GitHub release

Create a version tag to trigger the release workflow:

```bash
git tag v0.1.0
git push origin v0.1.0
```

A release is complete only after assets are visible on GitHub and downloaded successfully.
