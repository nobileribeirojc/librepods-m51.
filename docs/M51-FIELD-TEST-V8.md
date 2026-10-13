# Galaxy M51 / AirPods Pro 3 — field test sheet for v8+

The app is experimental. Build success on GitHub Actions is **not** proof of physical Bluetooth behavior.

## Before testing
- Install the requested experimental APK and verify it is the expected version under app information/diagnostics.
- Save any existing diagnostic export **before** uninstalling a differently signed build. Android may reject the APK as an update when debug signatures differ; uninstalling resets app preferences.
- Pair AirPods Pro 3 in Android Bluetooth. Check audio works independently of the app's AACP status.
- Grant required nearby-device/location permissions. Charge the case/earbuds enough to distinguish changes.
- Open CAPod for a direct comparison on the same phone. Compare measurements taken in the same case/earbud state and close together in time (public BLE advert measurements may be coarser).

## Fill in after each test

| ID | Operation on Galaxy M51 | Expected / acceptance criteria | Result |
|---|---|---|---|
| T01 | Launch app, Bluetooth ON, case open nearby | Scanner starts; proximity and Apple counters progress; Pro 3 candidate can be selected | ☐ |
| T02 | Show battery and compare CAPod left/right/case | Three separate current fields, clearly marked if BLE-unverified. Note public BLE rounding to 10% | ☐ |
| T03 | Leave one bud in case and one outside; compare CAPod | Left and right are not swapped; case is independent; no false case-open transition | ☐ |
| T04 | Put both buds in case, open/close lid twice | Popup reacts only to sufficiently reliable actual transitions, not repeated stale state | ☐ |
| T05 | Take earbuds out, move case away or stop advertising | Old BLE data becomes unknown/expired according to documented TTL, not stuck forever | ☐ |
| T06 | Toggle Bluetooth OFF then ON while app open | Scan stops/restarts and service is stable; no `lateinit` or `Service not registered` exception | ☐ |
| T07 | Switch screens and background/foreground app | No duplicate service bindings, frozen UI or sudden fake state | ☐ |
| T08 | Revoke permissions, then regrant | Clear permission message; scanner resumes without crash | ☐ |
| T09 | Screen OFF, wait, open case, then resume app | Report if Android throttles scanning; state must not falsely claim live data | ☐ |
| T10 | Optional: compare original and alternate classic L2CAP attempt | Record socket creation, connect duration, error category, and whether *valid AACP reply* arrived. Socket construction is not connection proof | ☐ |
| T11 | Optional ANC/Transparency command test only if valid AACP-ready | Actual physical state changes; no optimistic UI on failed write | ☐ |
| T12 | Restart phone / disable battery optimization if appropriate, repeat T01/T02 | Record Android optimization settings; no unexplained change in advertised identity | ☐ |

## What to share privately with Work
- Which APK version was installed; build/run number and the time of each test.
- For T02/T03, *current* three CAPod values and three LibrePods values, with earbud/case state. Previous `90/90/10` is historical, **not** today's expected value.
- Screenshots of diagnostic counters (BLE, Apple adverts, proximity, ignored) and a redacted M51 diagnostic export.
- A short description of what happened during T06 and T07; for L2CAP include duration and error classification from diagnostics.
- If safe and available, device-local bugreport/HCI only on explicit request; review/redact before sharing. **Do not publish raw Bluetooth MAC addresses, personal device names, secrets, or full traces in a public repo**.

## Interpretation
- BLE battery measurement, audio connected (A2DP/HFP), and ready AACP channel are three different facts.
- Public adverts have coarse (typically 10%) battery resolution and don't authenticate the paired AirPods.
- Case lid flags need reliable in-case context; stale values can otherwise trigger a misleading popup.
- `read failed, socket might closed or timeout, read ret: -1` does not by itself identify which Android-layer problem occurred.
