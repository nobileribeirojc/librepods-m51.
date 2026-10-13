#!/usr/bin/env python3
"""Final Android 12 L2CAP entry guard + quiet known-failure notices, preserve manual diagnostics.
Runs AFTER m51-p1-l2cap-guard.py. Incremental patch to original application only.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: python3 scripts/m51-p3-l2cap-quiet.py source/LibrePods-M51-v4")

root = Path(sys.argv[1]) / "android/app/src"
code = root / "main/java/me/kavishdevar/librepods"
service_file = code / "services/AirPodsService.kt"
onboarding_file = code / "screens/Onboarding.kt"
policy_file = code / "utils/M51ControlTransportPolicy.kt"
test_file = root / "test/java/me/kavishdevar/librepods/utils/M51ControlTransportPolicyTest.kt"

def patch(s, old, new, tag):
    count = s.count(old)
    if count != 1:
        raise RuntimeError(f"{tag}: expected exactly one source anchor, got {count}")
    return s.replace(old, new, 1)

service = service_file.read_text(encoding="utf-8")
onboarding = onboarding_file.read_text(encoding="utf-8")
policy = policy_file.read_text(encoding="utf-8")
tests = test_file.read_text(encoding="utf-8")

# Other callers may be added by future versions and takeover has a fourth call site.
# Guard at the ACTUAL socket entry, not only selected three call locations.
service = patch(service,
    """    fun connectToSocket(device: BluetoothDevice, useInsecureClassic: Boolean = false) {
        if (!l2capAttemptRunning.compareAndSet(false, true)) {""",
    """    fun connectToSocket(
        device: BluetoothDevice,
        useInsecureClassic: Boolean = false,
        explicitlyRequested: Boolean = false
    ) {
        if (!M51ControlTransportPolicy.mayAttempt(
                Build.VERSION.SDK_INT, explicitlyRequested
            )) {
            RootlessDiagnostics.stage("Android 12: L2CAP automático desativado; áudio A2DP e bateria BLE são independentes")
            return
        }
        if (!l2capAttemptRunning.compareAndSet(false, true)) {""",
    "L2CAP entry gate")

# No pop-up / high-priority notification for expected classic socket failures on API31/32.
# Failures remain in RootlessDiagnostics, including manual requests. Other Android versions unchanged.
service = patch(service,
    """    private fun showSocketConnectionFailureNotification(errorMessage: String) {
        val notificationManager = getSystemService(NotificationManager::class.java)""",
    """    private fun showSocketConnectionFailureNotification(errorMessage: String) {
        if (!M51ControlTransportPolicy.shouldShowFailureNotification(Build.VERSION.SDK_INT)) {
            Log.i("AirPodsService", "M51: L2CAP failure retained in diagnostics; high-priority notification suppressed on API 31/32")
            return
        }
        val notificationManager = getSystemService(NotificationManager::class.java)""",
    "quiet L2CAP failures")

onboarding = patch(onboarding,
    """                      try { service.connectToSocket(target, useInsecureClassic = insecureClassic) }""",
    """                      try { service.connectToSocket(
                          target, useInsecureClassic = insecureClassic,
                          explicitlyRequested = true
                      ) }""",
    "manual diagnostic allowed")

policy = patch(policy,
    """    fun allowAutomaticL2cap(sdkInt: Int): Boolean = sdkInt >= 33""",
    """    fun allowAutomaticL2cap(sdkInt: Int): Boolean = sdkInt >= 33
    fun mayAttempt(sdkInt: Int, explicitlyRequested: Boolean): Boolean =
        explicitlyRequested || allowAutomaticL2cap(sdkInt)
    fun shouldShowFailureNotification(sdkInt: Int): Boolean = sdkInt >= 33""",
    "transport behavior policy")
tests = patch(tests,
    """    @Test fun newerAndroidRetainsExistingBehavior() {""",
    """    @Test fun manualAacpRequestStillPermittedOnAndroid12() {
        assertTrue(M51ControlTransportPolicy.mayAttempt(31, true))
        assertFalse(M51ControlTransportPolicy.mayAttempt(31, false))
        assertFalse(M51ControlTransportPolicy.mayAttempt(32, false))
        assertTrue(M51ControlTransportPolicy.mayAttempt(33, false))
    }
    @Test fun knownM51SocketFailuresAreInDiagnosticsNotNotificationShade() {
        assertFalse(M51ControlTransportPolicy.shouldShowFailureNotification(31))
        assertFalse(M51ControlTransportPolicy.shouldShowFailureNotification(32))
        assertTrue(M51ControlTransportPolicy.shouldShowFailureNotification(33))
    }
    @Test fun newerAndroidRetainsExistingBehavior() {""",
    "regression tests")

# Commit only after all preconditions validated.
service_file.write_text(service, encoding="utf-8")
onboarding_file.write_text(onboarding, encoding="utf-8")
policy_file.write_text(policy, encoding="utf-8")
test_file.write_text(tests, encoding="utf-8")
print("PASS: Android12 L2CAP auto-gated at socket entry, quiet notification, explicit manual test preserved")
