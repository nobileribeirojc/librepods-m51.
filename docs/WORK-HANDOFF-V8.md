# LibrePods M51 — handoff to ChatGPT Work / Codex (2026-10-13)

## Objective
Incrementally improve **LibrePods M51 v8**, without restarting the application or requiring root. Target: Samsung Galaxy M51 / Android 12 (API 31) / AirPods Pro 3. **First prove stable, independent BLE battery values (left, right, case) on the physical phone.** Only then pursue AAP/AACP and interface polish.

## Verified repository state
- GitHub: https://github.com/nobileribeirojc/librepods-m51. (note the trailing dot in the actual repository name).
- Default branch: `main`. Baseline commit: [8e675f2](https://github.com/nobileribeirojc/librepods-m51./commit/8e675f2561425f401e26c234e2f1468f12501301).
- Build pipeline: `.github/workflows/build-m51-v4-from-zip.yml`, Java 17, Android SDK 35, `:app:testDebugUnitTest :app:assembleDebug`.
- [Actions run 38434922504](https://github.com/nobileribeirojc/librepods-m51./actions/runs/38434922504) completed successfully. `LibrePods-M51-v8-BLE-APK` and `M51-v8-test-reports` were uploaded.
- **No physical verification is implied by that result.** v8 code repairs Compose service binding/unbinding and retries BLE scan when Bluetooth turns ON. The BLE, popup, alternative L2CAP and controls still require real Samsung test cases.
- v8 documentation: `docs/M51-V8.md`; v7 details and static protocol assessment: `docs/M51-V7.md`.

## Construction map (source is inside ZIP)
1. Extract `LibrePods-M51-v4-pronto-para-compilar.zip` to `source/` (produces `source/LibrePods-M51-v4`).
2. `python3 scripts/fix-m51-unknown-battery.py source/LibrePods-M51-v4`
3. `python3 scripts/m51-v5-public-ble-preview.py source/LibrePods-M51-v4`
4. `python3 scripts/m51-v6-ble-continuo.py source/LibrePods-M51-v4`
5. `git apply --directory=source/LibrePods-M51-v4 scripts/m51-v7.patch`
6. `python3 scripts/m51-v8-lifecycle-ble.py source/LibrePods-M51-v4`
7. Build/test in `source/LibrePods-M51-v4/android`.

Shortcut: `bash scripts/materialize-m51-v8.sh`. The output `source/` is already gitignored. Don't modify the ZIP and forget the patch chain, or put an unreviewed generated tree into version control.

## Evidence versus remaining hypotheses
| Area | Currently supported evidence | What Work must establish |
|---|---|---|
| Build | Latest v8 GitHub Actions succeeded | Review test results, keep CI passing after changes |
| Audio | 2026-10-13 prior log identified paired/connected AirPods audio | Ensure A2DP/HFP status is independent from BLE and AACP |
| BLE scanner | Prior log showed scanner initially starting with BT OFF and later successful start | Capture real adverts on API 31, detect scan throttling/permissions, confirm foreground/background behavior |
| Three batteries | Decoder + tests in v7; public BLE values roughly 10% granularity; no v8 physical proof | Compare three *current* values with CAPod, verify independent fields and stale-value expiry |
| Popup | Optional candidate-based popup exists | Verify transitions, case context, no false popup on stale or different devices |
| L2CAP | Earlier six `BluetoothSocket.connect()` failures with `read ret: -1`; alternative constructor was added | Compare constructor, PSM, timing, auth, handshake logs; distinguish stack-level failure from app-level failure |
| Controls | AACP response is required even to show advanced controls | Do **not** state ANC/transparency functional before proof on M51 |
| Installation | Debug signing key may vary by CI runner | Preserve logs before uninstall. Decide stable signing via secure CI secret; never commit secret |

## Concrete upstream code to compare (do not indiscriminately paste)
**CAPod** (GitHub repository currently advertises GPL-3.0): https://github.com/d4rken-org/capod
- `app/src/main/java/eu/darken/capod/pods/core/apple/ble/devices/airpods/AirPodsPro3.kt`: model code and device-specific battery/case history.
- `app/src/main/java/eu/darken/capod/pods/core/apple/ble/devices/DualApplePods.kt`: left/right nibble flip, charge, and reliable lid-state context. Especially avoid a false open-case reading when only the out-of-case pod advertises.
- `app/src/main/java/eu/darken/capod/common/bluetooth/l2cap/L2capSocketFactory.kt`: API-dependent classic BR/EDR L2CAP socket creation; public API fallback targeting **API 37+ is not available on Android 12**.
- `app/src/main/java/eu/darken/capod/pods/core/apple/aap/AapConnectionManager.kt` and `.../aap/engine/AapConnection.kt`: lifecycle, connect timeout, handshake watchdog and packet framing. This is reference design, **not evidence** it connects on M51.
- `app/src/test/java/eu/darken/capod/pods/core/apple/ble/devices/airpods/AirPodsPro3Test.kt` and `.../aap/devices/airpods/AirPodsPro3AapSessionTest.kt`: inspect test cases and adapt compatible cases.

**LibrePods upstream** (repository currently advertises GPL-3.0): https://github.com/librepods-org/librepods
- `android/app/src/main/cpp/l2c_fcr_hook.cpp`: platform-stack hook. **Not applicable in a normal unprivileged Android 12 APK**.
- Compare packet protocol/Android source against the v4 ZIP before proposing a backport.

Follow the licenses and per-file headers; document precisely what was adapted and how distribution requirements will be met.

## Prioritized engineering queue

### P0 — BLE correctness (acceptance criteria)
- Investigate real advertiser parse results with opt-in diagnostics: manufacturer, model, packet shape/length, valid/invalid frame counts, scanner start/stop reason, timestamp/freshness, RSSI without exposing raw identifiers by default.
- Verify AirPods Pro 3 model match, pairing payload length, and nibble position (left/right flip based on status bit); the case is a third independent value.
- Explicitly distinguish `0%`, `unknown`, `stale` and `charging`; unknown reserved nibbles must not become a made-up 100%.
- Handle real changes and case open/close, one earbud outside case, address rotation, and no advertisement. No indefinite fake battery display.
- Provide an easy physical comparison using CAPod under identical conditions and the checklist in `M51-FIELD-TEST-V8.md`.

### P1 — lifecycle and diagnostics
- Review v8 `DisposableEffect` path: BT `STATE_ON` callback only calls `startScanning()` when `airPodsService.value` is present; check race if BT comes ON before service binds.
- Test permission grant/revoke, Activity recreation, navigating screens, app to background and back, screen-off scans, duplicate bind/unbind, and stalled UI frames.
- Ensure diagnostic exports classify `no scan / no Apple advert / no supported model / decoded unknown / stale / failed L2CAP` separately; preserve privacy.

### P2 — transport and control, contingent on P0
- Compare the existing v7 optional CAPod-style classic L2CAP constructor with modern CAPod `L2capSocketFactory`; this may affect socket creation but **cannot be assumed** to bypass an Android Bluetooth-stack refusal.
- Diagnose the six previous `read ret: -1` failures with safe, minimal logging and, if the user explicitly opts in, locally captured redacted Bluetooth HCI/bugreport. This error alone does not prove timeout.
- `createL2capChannel` / LE CoC is **not** a drop-in replacement for BR/EDR AACP PSM `0x1001`. Do not fake a 'connected' state.
- Keep ANC/Transparency/Adaptive commands inaccessible unless channel readiness and actual physical effect are proven.

### P3 — presentation and distribution
- Revisit simple UI with three independent battery indicators and clear AACP availability; no false attribution to a paired device from unverified BLE.
- Fix repeatable debug APK signing for incremental installs using GitHub Actions secrets/keystore without committing key material. Verify SHA-256 and provide release notes.

## Required Work output
1. Ranked root causes with links to source files and logs, evidence and uncertainty labels.
2. Focused code changes on a separate branch/PR, preserving all prior version history and identity.
3. Automated regression tests and successful build artifacts; explain failures, do not hide.
4. A plain-language changelog and the next minimal test on the **physical M51**.
5. A table marked `CI-verified` / `device-verified` / `not yet verified` for every feature.

## Practical next step for the user
After Work resets, open this handoff branch or its PR in the GitHub-connected Work session and request **P0 BLE verification/instrumentation first**. Do not start a fresh project. For physical tests, save/share the app's M51 diagnostic export privately and compare the current three values with CAPod; redact identifiers before putting anything in a public GitHub issue.
