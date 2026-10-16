# LibrePods M51 p9: non-destructive side-by-side test plan

Date: 2026-10-16. Original app and PR #4 are unchanged.

## Why a second applicationId

The p8 app installed on the Samsung M51 uses
`me.kavishdevar.librepods.m51test`. A locally compiled p9 APK was signed
with a different debug certificate. Android requires a compatible signer,
matching applicationId and a valid versionCode for in-place updates.
Do not uninstall p8 or assert that an APK's signature grants data migration.
Do not publish debug keystores, keys, private BLE logs or addresses.

This branch is an isolated experimental copy of the **same** LibrePods
sources (original v4 reconstructed through v9, p0–p9). It applies
`scripts/m51-p9-sidecar.py` only after all previous scripts:

- Debug `applicationIdSuffix = ".p9sidecar"`; resulting app ID:
  `me.kavishdevar.librepods.m51test.p9sidecar`.
- Distinct app label: LibrePods M51 p9 (paralelo).
- BootReceiver disabled in this **test variant** to avoid automatically
  starting a second BLE scanner on boot. An explicit app launch can start
  a scan, so never run both simultaneously.
- Resource URI authority uses the running app's package, while
  `FileProvider` already uses `${applicationId}.provider`.
- No changes to the original Android package namespace, p0–p9 parsing,
  L2CAP transport, test fixtures or signatures in the p8 application.

This installation does not overwrite, delete, recover, or share the
p8 app's data. Sidecar permissions, settings and any per-app Bluetooth
identity material are separate and must be granted/set up independently.

## Automated verification

Workflow: [isolated p9 sidecar build](https://github.com/nobileribeirojc/librepods-m51./actions/workflows/build-m51-p9-sidecar.yml).
GitHub run: [38983101104](https://github.com/nobileribeirojc/librepods-m51./actions/runs/38983101104).
Source commit: `ab7fa0af74d907f22e2784a680aa00335d4ca12b`.

The workflow reconstructs unchanged LibrePods sources through p9, runs
`verify-m51-audit.py`, runs JUnit tests, assembles debug, asserts a distinct
applicationId, checks the application label and unique provider authority,
verifies APK signing with apksigner, and emits SHA256 provenance.

A successful CI run **does not** validate BLE on the physical handset.
Never treat one manually replayed p8 frame as a p9 runtime test.

## Next authorized physical session (not executed remotely)

Only after user explicitly approves installation of the sidecar APK:

1. Preserve p8 and any available local logs/preferences; do not reset its data.
   On Windows/ADB verify both package IDs with
   `adb shell pm list packages | findstr librepods`.
2. Stop p8's process without uninstalling or clearing its data:
   `adb shell am force-stop me.kavishdevar.librepods.m51test`.
   Keep CAPod closed except for deliberate reference measurements.
3. Install the separately named candidate APK after checking its
   manifest package and SHA256; do not use it as an in-place p8 update.
4. Open p9 sidecar, separately allow Bluetooth scan/connect and location
   permissions needed for the existing app. Opt in to overlay only when
   popup testing; do not presume permissions transfer from p8.
5. With AirPods in case, capture time-marked opening, steady lid, each
   ear removed/replaced, closure, and reconnect; retain raw HCI/ADB data
   locally and never commit MAC addresses or crypto payloads.
6. Record left/right/case values in CAPod and p9 in matched short windows,
   with timestamps. Do not assume channel/ear swap from asynchronous captures.
7. Measure steady-state updates (incl. cache expiry), scanner retry counts,
   app foreground/background, case popup, and if authenticated events exist
   in-ear pause/resume. No automatic media action without reliable evidence.
8. Measure L2CAP/AACP separately from audio A2DP; do not claim ANC or
   transparency from BLE battery frames.
9. Avoid running p8 and p9 scanner processes concurrently. The test variant
   can be uninstalled independently, but any sidecar-specific data would be lost.

## Current constraints

- p9's 41 JUnit tests and Android compilation are documented in the
  original audit reports; physical validation of the **p9 binary** is pending.
- On p8, a controlled scan replay produced one UI observation
  left 80%, right 70%, case 50%; CAPod showed 70/80/50 at a
  different time, not a synchronized left/right comparison.
- Original signer is not currently available for an in-place update.
  A certificate embedded in an APK does not contain the private signing key.
- Android 12 backups are configuration- and policy-dependent: no reliable
  zero-loss migration has yet been demonstrated; do not wipe p8.
- The local p9 report `docs/M51-P9-LOCAL-BUILD-2026-10-16.md` may still
  be solely on the Windows laptop. Preserve it; do not pretend it is uploaded.
