# Codex work instructions — LibrePods M51

This is **the existing LibrePods M51 Android application**, not a blank template. Work on `m51-root-cause-audit`, preserving `main` and PR #4. Never merge automatically or publish a user-installable APK unless expressly requested after evidence-based tests.

## Current mission

Read `docs/REA-CODEX-M51.md` and `docs/M51-ROOT-CAUSE-AUDIT.md` first. Target Samsung Galaxy M51 SM-M515F, Android 12/API 31, AirPods Pro 3, **no root**. Prioritize independent public BLE battery readings (left/right/case), audio A2DP/HFP state, optional case popup, and evidence for in-ear events. Do not conflate these with Apple AACP features.

If REA is not installed and the user wants REA integration, propose the official `npx rea-agents@latest setup` plan, request approval for configuration changes and verify an actual Codex MCP connection before using it. Never claim an REA run happened without evidence. For APK analysis REA needs the APK plus JADX/JDK; for handset observations it needs authorized ADB access. Use open-source CAPod/OpenPods and the user's own LibrePods binaries where possible.

The Android application is reconstructed from the original v4 ZIP through ordered scripts and patches in `.github/workflows/audit-v8-source.yml`. `scripts/m51-p7-single-scanner.py` guards against duplicate scan callbacks on BLE filter fallback; verify that stopping the previous callback happens before registering a new one.

Evidence is mandatory: source/method references, CI run/results, packet format or device log where authorized, and explicit unknowns. In particular an Android 12 classic BR/EDR L2CAP/AACP connection is **not** proven by the existence of a socket. Never substitute LE CoC for classical L2CAP PSM `0x1001`, invent battery values, or report ANC/Transparency working absent an actual response.

After any code change, run unit tests and assembleDebug through CI, report exact tests, and await device validation. Preserve licenses and keep public logs free from identifying Bluetooth addresses.
