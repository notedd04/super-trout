# Risk Register

| Risk | Impact | Mitigation / status |
|---|---|---|
| Private forwarded ports cannot authenticate in WebView | Desktop unavailable on Android | Requires real GitHub-authenticated mobile test; fallback is device browser or an authenticated gateway |
| Codespaces has no stable public desktop protocol | NAT/session failures | noVNC private port is service-owned and reconnectable |
| GPU unavailable | Lightweight gaming only | Real GPU capabilities will not be claimed |
| Machine sizes unavailable | Provisioning failure | Render only machine choices returned by GitHub |
| Codespace data deleted | User data loss | Persistent workspace guidance, exports, Git workflows, and destructive-operation warnings |
| Mobile input latency | Poor usability | noVNC touch, virtual keyboard, adaptive quality, reconnection |
| Android WebView certificate/cookie behavior | Authentication failure | Live device testing and browser fallback |
