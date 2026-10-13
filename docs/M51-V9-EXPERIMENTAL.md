# LibrePods M51 v9 BLE recovery — experimental, not yet device-validated

Target: Samsung Galaxy M51, Android 12/API 31, AirPods Pro 3, no root. The original v4 package, version history and application ID are retained. This is an incremental patch applied **after** the v8 reconstruction, not an alternative application.

## Source changes
The script `scripts/m51-v9-ble-recovery.py` runs after `scripts/materialize-m51-v8.sh` and patches:
- `utils/BLEManager.kt`: the 6-second scan restart cooldown is now stamped **only after** a non-null Android BLE scanner accepted `startScan(...)`; previous code stamped the cooldown before checking/scanning, even when Bluetooth was switched OFF and the scanner was absent. Null scanner is surfaced in diagnostic scan status.
- `MainActivity.kt`: an `ACTION_STATE_CHANGED / STATE_ON` broadcast may arrive before asynchronous `AirPodsService` binding completes. A single atomic pending flag now remembers that event and requests a BLE scan once the service is bound. This is a lifecycle recovery, not a root or L2CAP workaround.
- `android/app/build.gradle.kts`: `versionCode=19`, `versionName=0.1.0-rc.4-m51-v9-ble-recovery`.

No new AACP packets, socket types, BLE identity assumptions, ANC or transparency functionality have been added.

## Limitations and validation
A successful GitHub Actions build/tests is a code-level result only; it **cannot** verify scanner behavior or battery values on the actual Samsung device.

Physical tests to perform:
1. Start app while Bluetooth is OFF, then turn Bluetooth ON: scanner should recover and counters increase with case open nearby.
2. Toggle Bluetooth OFF/ON rapidly (under 6 seconds) with the app foregrounded. Earlier unsuccessful starts must not trigger artificial cooldown. A previous **successful** scan can still produce the documented 6-second throttle; this is intentional.
3. Repeat with quick Activity navigation and permission grant, and with app background/foreground; no service receiver/bind exceptions.
4. Compare three separate values with CAPod in the same physical state. This patch is scan recovery only; it does **not** claim to have solved unknown battery values.
5. Export redacted diagnostics privately, not as a public GitHub attachment containing device identifiers.

**Expected status:** CI verification only until the M51 tests finish. The BLE decoder, popup, case cache, and classic BR/EDR L2CAP are inherited from v8; L2CAP `read ret: -1` may remain.

## Source
- v8 baseline: `docs/M51-V8.md`, and `docs/WORK-HANDOFF-V8.md`.
- Latest user-facing test matrix: `docs/M51-FIELD-TEST-V8.md`.
