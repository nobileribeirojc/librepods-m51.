#!/usr/bin/env python3
"""Apply after p7. Preserve prior fixes; no APK, root or protocol claims."""
from pathlib import Path
import sys

root = Path(sys.argv[1]) / 'android/app/src'
main = root / 'main/java/me/kavishdevar/librepods'
tests = root / 'test/java/me/kavishdevar/librepods/utils'
changes = {}

def edit(relative, old, new):
    path = main / relative
    source = changes.get(path, path.read_text(encoding='utf-8'))
    if source.count(old) != 1:
        raise RuntimeError(f'{relative}: expected one anchor: {old[:80]!r}')
    changes[path] = source.replace(old, new, 1)

edit('utils/BLEManager.kt', 'fun startScanning(unfiltered: Boolean = false) {',
     'fun startScanning(unfiltered: Boolean = false, automaticRetry: Boolean = false) {\n'
     '        if (!automaticRetry) m51ScanPolicy.reset()')
for old, new in [
    ('if (!m51StoppedByUser) startScanning(unfiltered = unfiltered)',
     'if (!m51StoppedByUser) startScanning(unfiltered = unfiltered, automaticRetry = true)'),
    ('if (!m51StoppedByUser) startScanning(unfiltered = next.unfiltered)',
     'if (!m51StoppedByUser) startScanning(unfiltered = next.unfiltered, automaticRetry = true)'),
    ('                        startScanning(unfiltered = true)',
     '                        startScanning(unfiltered = true, automaticRetry = true)'),
    ('override fun onScanResult(callbackType: Int, result: ScanResult) {\n                    processScanResult(result)',
     'override fun onScanResult(callbackType: Int, result: ScanResult) {\n'
     '                    if (mScanCallback !== this) return\n                    processScanResult(result)'),
    ('override fun onBatchScanResults(results: List<ScanResult>) {\n                    processedAddresses.clear()',
     'override fun onBatchScanResults(results: List<ScanResult>) {\n'
     '                    if (mScanCallback !== this) return\n                    processedAddresses.clear()'),
    ('                    val next = m51ScanPolicy.failed(errorCode)\n',
     '                    val next = m51ScanPolicy.failed(errorCode)\n'
     '                    if (next == null) {\n'
     '                        RootlessDiagnostics.scanStatus = "BLE interrompido (código $errorCode); verifique Bluetooth/permissões e reinicie a busca manualmente"\n'
     '                        return\n'
     '                    }\n'),
]:
    edit('utils/BLEManager.kt', old, new)

policy = main / 'utils/M51ScanRecoveryPolicy.kt'
changes[policy] = '''/* LibrePods M51 extension, AGPL-3.0-or-later. */
package me.kavishdevar.librepods.utils

internal class M51ScanRecoveryPolicy {
    data class Retry(val delayMs: Long, val unfiltered: Boolean)
    private var consecutiveFailures = 0

    // Android ScanCallback values: 2 registration, 3 internal, 5 resources,
    // 6 too frequent. Unsupported features (4), already started (1), and
    // unrecognized errors require explicit recovery, not an infinite loop.
    @Synchronized fun failed(errorCode: Int): Retry? {
        consecutiveFailures++
        if (errorCode !in setOf(2, 3, 5, 6) || consecutiveFailures >= 5) return null
        val delay = when {
            errorCode == 6 -> 30_000L
            consecutiveFailures == 1 -> 8_000L
            consecutiveFailures == 2 -> 15_000L
            else -> 30_000L
        }
        return Retry(delay, consecutiveFailures >= 2)
    }

    @Synchronized fun reset() { consecutiveFailures = 0 }
    @Synchronized fun appleSeen() { reset() }

    fun remainingCooldownMs(lastStartedMs: Long?, nowMs: Long): Long {
        if (lastStartedMs == null || nowMs < lastStartedMs) return 0L
        return (6_000L - (nowMs - lastStartedMs)).coerceAtLeast(0L)
    }
}
'''

edit('utils/PublicProximity.kt',
     'val leftInEar: Boolean, val rightInEar: Boolean, val lidOpen: Boolean',
     'val leftInEar: Boolean, val rightInEar: Boolean, val lidOpen: Boolean,\n'
     '        val lidKnown: Boolean')
edit('utils/PublicProximity.kt', '            reliableLid && byte(8) and 8 == 0\n',
     '            reliableLid && byte(8) and 8 == 0,\n            reliableLid\n')
edit('utils/BLEManager.kt', '        val lidOpen: Boolean = false,',
     '        val lidOpen: Boolean = false,\n        val lidKnown: Boolean = true,')
edit('utils/BLEManager.kt', '            lidOpen = reading.lidOpen,',
     '            lidOpen = reading.lidOpen, lidKnown = reading.lidKnown,')
edit('utils/CasePopupPolicy.kt', 'nowMs: Long, address: String = ""): Boolean {',
     'nowMs: Long, address: String = "", lidKnown: Boolean = true): Boolean {\n'
     '        // Unknown is not a closing transition and must not rearm the popup.\n'
     '        if (!lidKnown) return false')
edit('services/AirPodsService.kt', '                    address = device.address\n',
     '                    address = device.address,\n                    lidKnown = device.lidKnown\n')
edit('utils/RootlessDiagnostics.kt', 'failureCategory = "Nenhuma: L2CAP estabelecido"',
     'failureCategory = "Socket conectado; AACP ainda não confirmado"')

scan_tests = '''package me.kavishdevar.librepods.utils
import org.junit.Assert.*
import org.junit.Test

class M51ScanRecoveryPolicyTest {
    @Test fun transientFailuresBackOffAndStopAtFifthFailure() {
        val p = M51ScanRecoveryPolicy()
        assertEquals(M51ScanRecoveryPolicy.Retry(8_000, false), p.failed(2))
        assertEquals(M51ScanRecoveryPolicy.Retry(15_000, true), p.failed(3))
        assertEquals(M51ScanRecoveryPolicy.Retry(30_000, true), p.failed(5))
        assertEquals(M51ScanRecoveryPolicy.Retry(30_000, true), p.failed(2))
        assertNull(p.failed(2))
        repeat(20) { assertNull(p.failed(2)) }
    }
    @Test fun permanentAndUnknownErrorsDoNotRetry() {
        for (code in listOf(1, 4, 0, 99)) assertNull(M51ScanRecoveryPolicy().failed(code))
    }
    @Test fun rateLimitWaitsAtLeastThirtySeconds() {
        assertEquals(M51ScanRecoveryPolicy.Retry(30_000, false), M51ScanRecoveryPolicy().failed(6))
    }
    @Test fun explicitRestartAndValidFrameResetFailureBudget() {
        val p = M51ScanRecoveryPolicy()
        repeat(5) { p.failed(2) }; p.reset()
        assertEquals(M51ScanRecoveryPolicy.Retry(8_000, false), p.failed(2))
        repeat(5) { p.failed(2) }; p.appleSeen()
        assertEquals(M51ScanRecoveryPolicy.Retry(8_000, false), p.failed(2))
    }
    @Test fun cooldownRequestsAreDelayedNotSilentlyDropped() {
        val p = M51ScanRecoveryPolicy()
        assertEquals(5_500L, p.remainingCooldownMs(1_000L, 1_500L))
        assertEquals(0L, p.remainingCooldownMs(1_000L, 7_000L))
        assertEquals(0L, p.remainingCooldownMs(null, 500L))
    }
}
'''
changes[tests / 'M51ScanRecoveryPolicyTest.kt'] = scan_tests
popup = tests / 'CasePopupPolicyTest.kt'
source = popup.read_text(encoding='utf-8')
anchor = 'class CasePopupPolicyTest {'
if source.count(anchor) != 1: raise RuntimeError('popup test anchor')
changes[popup] = source.replace(anchor, anchor + '''
    @Test fun unknownLidDoesNotCreateAClosingTransition() {
        val p = CasePopupPolicy()
        assertTrue(p.canShow("AirPods Pro 3", true, -40, true, true, 0, "A"))
        p.onShown(0)
        // Keep receiving known OPEN, beyond the global cooldown.
        for (t in 1_000L..60_000L step 1_000L) {
            assertFalse(p.canShow("AirPods Pro 3", true, -40, true, true, t, "A"))
        }
        assertFalse(p.canShow("AirPods Pro 3", true, -40, true, true, 60_001, "A"))
        assertFalse(p.canShow("AirPods Pro 3", false, -40, true, true, 60_002, "A", lidKnown = false))
        assertFalse(p.canShow("AirPods Pro 3", true, -40, true, true, 60_003, "A"))
        assertFalse(p.canShow("AirPods Pro 3", false, -40, true, true, 60_004, "A"))
        assertTrue(p.canShow("AirPods Pro 3", true, -40, true, true, 60_005, "A"))
    }
''', 1)
decoder_tests = tests / 'PublicProximityTest.kt'
source = decoder_tests.read_text(encoding='utf-8')
anchor = '    @Test fun earOrientationMatchesPrimaryAndCase() {'
if source.count(anchor) != 1: raise RuntimeError('decoder test anchor')
changes[decoder_tests] = source.replace(anchor, '''    @Test fun lidUnknownIsDistinctFromKnownClosed() {
        assertFalse(PublicProximity.decode(frame(status = 0x10))!!.lidKnown)
        assertTrue(PublicProximity.decode(frame(lid = 8))!!.lidKnown)
        assertFalse(PublicProximity.decode(frame(lid = 8))!!.lidOpen)
    }
''' + anchor, 1)

# Validate every anchor before writing any source.
for path, source in changes.items():
    path.write_text(source, encoding='utf-8', newline='\n')
print('PASS: finite scan retries, stale callback guard, unknown lid preserved, honest socket diagnostic')
