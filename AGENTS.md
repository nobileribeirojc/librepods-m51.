# AGENTS.md — LibrePods M51

This is a continuation of the **existing** LibrePods M51 adaptation, **not** a new Android app. The user targets **Samsung Galaxy M51 (SM-M515F), Android 12 / API 31, AirPods Pro 3, no root**.

## First read
- `README.md`, `docs/M51-V7.md`, `docs/M51-V8.md`, `docs/WORK-HANDOFF-V8.md`, and `docs/M51-FIELD-TEST-V8.md`.
- The original v4 application is archived at `LibrePods-M51-v4-pronto-para-compilar.zip` and is reconstructed by `.github/workflows/build-m51-v4-from-zip.yml`.
- Scripts are applied in order: `fix-m51-unknown-battery.py`, `m51-v5-public-ble-preview.py`, `m51-v6-ble-continuo.py`, `m51-v7.patch`, `m51-v8-lifecycle-ble.py`.
- Use `bash scripts/materialize-m51-v8.sh` to create the exact current project under ignored `source/LibrePods-M51-v4`. The script refuses to overwrite an existing extracted source.
- Baseline on 2026-10-13: commit `8e675f2561425f401e26c234e2f1468f12501301`; successful Actions run `38434922504`. CI success proves only build/unit-test success.

## Non-negotiable constraints
1. Preserve the original app identity: `me.kavishdevar.librepods.m51test`, existing service, onboarding, and user settings. Do not create a replacement app.
2. No root, Xposed/Magisk, privileged Bluetooth-service patches, or invented Bluetooth endpoints. Android 12 platform limitations must be reported honestly.
3. Treat public BLE advertisements as **unverified**: do not falsely equate an address/name/RSSI or a proximity packet with the connected, bonded AirPods.
4. A2DP/HFP audio connection, BLE visibility, BR/EDR L2CAP socket, and an actual AACP/AAP-ready control channel are distinct states.
5. Preserve three independent battery fields (left, right, case), with **0% valid**, unknown values unknown, explicit freshness expiry, and 10%-resolution limitations for public BLE.
6. Do not claim ANC, Transparency, Adaptive Audio, or a command worked unless the specific control was tested on the user's M51 with observable confirmation.
7. Before copying third-party code, check per-file licenses and notices. Base declares AGPL-3.0-or-later; CAPod and upstream repositories advertise GPL-3.0. Record attribution and compatibility reasoning.
8. Never commit a signing keystore, private key, real Bluetooth address, HCI dump containing identifying data, access token, or sensitive raw user log. Redact diagnostics before public publication.

## Development method
- Work on a feature branch, review diffs, and open a pull request; do not replace the v8 baseline unreviewed.
- Prefer focused, reproducible source patches/scripts or an explicitly reviewed move to tracked source. Keep failure-on-anchor-mismatch checks until the layout is normalized.
- If a change modifies a production file, run Gradle unit tests + debug assemble on the reconstructed project; inspect the GitHub Actions run and generated artifacts. CI does **not** emulate the Samsung Bluetooth stack.
- Add tests for BLE parsing (valid 0/10/100; F and reserved B–E unknown), nibble flip, case context and lid reliability, address rotation/expiration, repeated scans, and service lifecycle.
- Prioritize reliable **BLE battery and diagnostics** before experimental L2CAP. Do not silently substitute LE CoC, RFCOMM, or generic GATT for the classic AACP channel.

## Reproduction
```bash
bash scripts/materialize-m51-v8.sh
cd source/LibrePods-M51-v4/android
chmod +x gradlew
./gradlew :app:testDebugUnitTest :app:assembleDebug --no-daemon --stacktrace
```
Requires Android SDK/platform 35, build tools 35, and Java 17 (same as workflow). Compare behavior against `docs/M51-FIELD-TEST-V8.md` on physical hardware.

## Definition of done
For each proposed feature: code diff, tests, successful APK build, clear diagnostics, a physical test case, and a result labeled **verified on device / CI-only / still unverified**. Do not automatically merge speculative changes.
