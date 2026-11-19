# Known limitations

- Live GitHub/Codespaces account testing is required before this can be considered verified on a real Android device.
- Private forwarded-port behavior in Android WebView is subject to GitHub authentication and mobile cookie handling.
- Codespaces machine sizes are account/organization-dependent and must be supplied dynamically.
- No GPU capability is available in the baseline Codespaces architecture.
- noVNC performance depends on mobile bandwidth and container CPU.
- Audio, clipboard, and file-transfer behavior require live validation.
- GitHub OAuth/device authorization is not yet implemented in the Android UI; the backend accepts bearer tokens supplied securely.
- The release APK is unsigned unless supplied signing secrets through GitHub Actions.
