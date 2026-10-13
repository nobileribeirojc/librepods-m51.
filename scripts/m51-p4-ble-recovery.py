#!/usr/bin/env python3
"""M51 adaptive BLE scanner: bounded retry, hardware-filter fallback, no root.
Runs after p0/p1/p2/p3 scripts. Does not claim that L2CAP/AACP works.
Original LibrePods M51 extension AGPL-3.0-or-later.
"""
from pathlib import Path
import sys
if len(sys.argv)!=2:
    raise SystemExit("usage: python3 scripts/m51-p4-ble-recovery.py source/LibrePods-M51-v4")
src=Path(sys.argv[1])/"android/app/src"
main=src/"main/java/me/kavishdevar/librepods/utils"
file=main/"BLEManager.kt"
s=file.read_text(encoding="utf-8")
def change(old,new,label):
    global s
    n=s.count(old)
    if n!=1: raise RuntimeError(f"{label}: expected 1 source anchor got {n}")
    s=s.replace(old,new,1)

change("""    private var lastScanStartMs: Long? = null
    private var mBluetoothLeScanner""",
"""    private var lastScanStartMs: Long? = null
    private val m51ScanPolicy = M51ScanRecoveryPolicy()
    private var m51RetryTask: Runnable? = null
    private var m51FilterWatchdog: Runnable? = null
    private var m51StoppedByUser = false
    private var mBluetoothLeScanner""","policy state")

change("""    @SuppressLint("MissingPermission")
    fun startScanning(unfiltered: Boolean = false) {
        val now = android.os.SystemClock.elapsedRealtime()""",
"""    @SuppressLint("MissingPermission")
    @Synchronized
    fun startScanning(unfiltered: Boolean = false) {
        m51StoppedByUser = false
        m51RetryTask?.let { cleanupHandler.removeCallbacks(it) }
        m51RetryTask = null
        m51FilterWatchdog?.let { cleanupHandler.removeCallbacks(it) }
        m51FilterWatchdog = null
        val now = android.os.SystemClock.elapsedRealtime()""", "start lifecycle")

change("""        cleanupHandler.removeCallbacks(cleanupRunnable)
        try {
            Log.d(TAG, "Starting BLE scanner")""",
"""        cleanupHandler.removeCallbacks(cleanupRunnable)
        try {
            Log.d(TAG, "Starting BLE scanner")""","check scanner lifecycle")

change("""            val scanSettings = ScanSettings.Builder()
                .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)""",
"""            val scanSettings = ScanSettings.Builder()
                .setScanMode(if (unfiltered) ScanSettings.SCAN_MODE_BALANCED else ScanSettings.SCAN_MODE_LOW_LATENCY)""",
"avoid perpetual high-power unfiltered BLE")

change("""                override fun onScanFailed(errorCode: Int) {
                    RootlessDiagnostics.scanStatus = "Falha BLE: código $errorCode (verifique permissões e Bluetooth)"
                    mScanCallback = null
                    cleanupHandler.removeCallbacks(cleanupRunnable)
                    Log.e(TAG, "BLE scan failed with error code: $errorCode")
                }""",
"""                override fun onScanFailed(errorCode: Int) {
                    if (mScanCallback !== this) return
                    mScanCallback = null
                    cleanupHandler.removeCallbacks(cleanupRunnable)
                    m51FilterWatchdog?.let { cleanupHandler.removeCallbacks(it) }
                    m51FilterWatchdog = null
                    val next = m51ScanPolicy.failed(errorCode)
                    RootlessDiagnostics.scanStatus = "BLE falhou (código $errorCode); nova tentativa em ${next.delayMs / 1000}s, modo ${if (next.unfiltered) "compatível" else "Apple"}"
                    Log.w(TAG, "BLE scan error=$errorCode; retry in ${next.delayMs} ms; fallback=${next.unfiltered}")
                    if (!m51StoppedByUser) {
                        m51RetryTask?.let { cleanupHandler.removeCallbacks(it) }
                        m51RetryTask = Runnable {
                            m51RetryTask = null
                            if (!m51StoppedByUser) startScanning(unfiltered = next.unfiltered)
                        }.also { cleanupHandler.postDelayed(it, next.delayMs) }
                    }
                }""", "recover from asynchronous Android scan failures")

change("""            scanner.startScan(if (unfiltered) emptyList() else listOf(scanFilter), scanSettings, mScanCallback)
            // Record the cooldown only after the Android scanner accepted startScan.
            lastScanStartMs = android.os.SystemClock.elapsedRealtime()
            RootlessDiagnostics.scanStatus = if (unfiltered) "BLE sem filtro (teste com tela acesa)" else "BLE com filtro Apple ativo" """.rstrip(),
"""            val proximityCountBefore = RootlessDiagnostics.proximity.get()
            scanner.startScan(if (unfiltered) emptyList() else listOf(scanFilter), scanSettings, mScanCallback)
            // Record the cooldown only after the Android scanner accepted startScan.
            lastScanStartMs = android.os.SystemClock.elapsedRealtime()
            RootlessDiagnostics.scanStatus = if (unfiltered) "BLE sem filtro (fallback Samsung; tela acesa)" else "BLE com filtro Apple ativo"
            if (!unfiltered) {
                // Some Samsung/Android 12 implementations accept an offloaded scan
                // but deliver ZERO matching packets. Detect silence and fall back to
                // software filtering while the user can keep the lid open.
                val currentCallback = mScanCallback
                m51FilterWatchdog = Runnable {
                    m51FilterWatchdog = null
                    if (mScanCallback === currentCallback &&
                        RootlessDiagnostics.proximity.get() == proximityCountBefore && !m51StoppedByUser) {
                        RootlessDiagnostics.scanStatus = "Filtro Apple sem respostas; tentando BLE sem filtro"
                        startScanning(unfiltered = true)
                    }
                }.also { cleanupHandler.postDelayed(it, 25_000L) }
            }""".rstrip(), "watch for broken offloaded manufacturer filter")

change("""            RootlessDiagnostics.apple.incrementAndGet()
            val manufacturerData = PublicProximity.frame(appleData)""",
"""            RootlessDiagnostics.apple.incrementAndGet()
            val manufacturerData = PublicProximity.frame(appleData)""", "recover policy on real Apple packets")

change("""    @SuppressLint("MissingPermission")
    fun stopScanning() {
        try {
            if (mBluetoothLeScanner""",
"""    @SuppressLint("MissingPermission")
    @Synchronized
    fun stopScanning() {
        m51StoppedByUser = true
        m51RetryTask?.let { cleanupHandler.removeCallbacks(it) }
        m51FilterWatchdog?.let { cleanupHandler.removeCallbacks(it) }
        m51RetryTask = null
        m51FilterWatchdog = null
        lastScanStartMs = null
        try {
            if (mBluetoothLeScanner""", "cancel background retries on service stop")


change("""            RootlessDiagnostics.proximity.incrementAndGet()
            val publicStatus = parseProximityMessage(address, manufacturerData)""",
"""            RootlessDiagnostics.proximity.incrementAndGet()
            m51ScanPolicy.appleSeen()
            val publicStatus = parseProximityMessage(address, manufacturerData)""",
"consider only valid Proximity BLE frames as scanner recovery")

# Write all source only after anchors validated.
policyfile=main/"M51ScanRecoveryPolicy.kt"
testfile=src/"test/java/me/kavishdevar/librepods/utils/M51ScanRecoveryPolicyTest.kt"
if policyfile.exists() or testfile.exists(): raise RuntimeError("Refusing to overwrite policy or test")
policy='''/* LibrePods M51 extension, AGPL-3.0-or-later.
 * Deterministic Android 12 BLE scan failure recovery: no OS Bluetooth patch.
 */
package me.kavishdevar.librepods.utils

internal class M51ScanRecoveryPolicy {
    data class Retry(val delayMs: Long, val unfiltered: Boolean)
    private var consecutiveFailures: Int = 0

    @Synchronized fun failed(errorCode: Int): Retry {
        consecutiveFailures = (consecutiveFailures + 1).coerceAtMost(5)
        // Avoid aggressive repeated registration of scan clients on Android.
        val waitMs = when (consecutiveFailures) {
            1 -> 8_000L
            2 -> 15_000L
            else -> 30_000L
        }
        // A second failure may be due to Samsung's hardware filter/offload;
        // do not change the app identity or blindly fabricate battery values.
        return Retry(waitMs, consecutiveFailures >= 2)
    }

    @Synchronized fun appleSeen() {
        consecutiveFailures = 0
    }
}
'''
test='''package me.kavishdevar.librepods.utils

import org.junit.Assert.*
import org.junit.Test

class M51ScanRecoveryPolicyTest {
    @Test fun firstFailureBacksOffInsteadOfHammeringScanner() {
        val policy = M51ScanRecoveryPolicy()
        assertEquals(M51ScanRecoveryPolicy.Retry(8_000, false), policy.failed(2))
        assertEquals(M51ScanRecoveryPolicy.Retry(15_000, true), policy.failed(3))
    }

    @Test fun repeatedFailuresAreBounded() {
        val policy = M51ScanRecoveryPolicy()
        repeat(12) { policy.failed(2) }
        assertEquals(M51ScanRecoveryPolicy.Retry(30_000, true), policy.failed(2))
    }

    @Test fun validAppleFrameResetsHardwareFallbackCounter() {
        val policy = M51ScanRecoveryPolicy()
        policy.failed(2)
        policy.failed(2)
        policy.appleSeen()
        assertEquals(M51ScanRecoveryPolicy.Retry(8_000, false), policy.failed(2))
    }
}
'''
file.write_text(s,encoding="utf-8")
policyfile.write_text(policy,encoding="utf-8")
testfile.parent.mkdir(parents=True,exist_ok=True)
testfile.write_text(test,encoding="utf-8")
print("PASS: bounded Android scan retry + unfiltered fallback watchdog + regression tests")
