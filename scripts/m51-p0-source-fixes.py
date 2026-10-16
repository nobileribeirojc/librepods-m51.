#!/usr/bin/env python3
"""Audited battery/audio fixes applied after v8. Not a new app or a release."""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: python3 scripts/m51-p0-source-fixes.py source/LibrePods-M51-v4")

root = Path(sys.argv[1]) / "android/app/src"
src = root / "main/java/me/kavishdevar/librepods"
tests = root / "test/java/me/kavishdevar/librepods/utils"

def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f"{label}: expected 1 anchor, got {n}")
    return text.replace(old, new, 1)

service_file = src / "services/AirPodsService.kt"
service = service_file.read_text(encoding="utf-8")
service = replace_once(service,
    "import me.kavishdevar.librepods.utils.CasePopupPolicy\n",
    "import me.kavishdevar.librepods.utils.CasePopupPolicy\nimport me.kavishdevar.librepods.utils.M51AutoBatteryPolicy\n",
    "policy import")
service = replace_once(service,
    "    private var lastManualBleUiMs = 0L\n",
    """    private var lastManualBleUiMs = 0L

    // Separate, explicitly UNVERIFIED BLE readings from AACP. Public addresses rotate.
    private val m51AutoBatteryPolicy = M51AutoBatteryPolicy()
    private var m51AutoExpiry: Runnable? = null
    private var m51AutoAddress: String? = null
    private var m51LastAutoUiMs = 0L
    private var m51LastBondMs = -10_000L
    private var m51HasBond = false
""",
    "BLE auto state")
service = replace_once(service,
    "    private fun receiveVerifiedBleBattery(status: BLEManager.AirPodsStatus) {",
    """    private fun receiveAutomaticNearbyBattery(status: BLEManager.AirPodsStatus, rssiDbm: Int) {
        if (status.model != "AirPods Pro 3") return
        val now = android.os.SystemClock.elapsedRealtime()
        if (now - m51LastBondMs >= 5_000L) {
            m51HasBond = hasBondedAirPodsForNearbyPopup()
            m51LastBondMs = now
        }
        val decision = m51AutoBatteryPolicy.observe(status.address, rssiDbm, m51HasBond, now)
        if (decision != M51AutoBatteryPolicy.Decision.CHOSEN_SOURCE) return
        manualBleHandler.post {
            // Never replace an explicitly selected source or a working AACP channel.
            if (manualBleAddress != null || (isConnectedLocally && aacpReady)) return@post
            val uiNow = android.os.SystemClock.elapsedRealtime()
            if (m51AutoAddress == status.address && uiNow - m51LastAutoUiMs < 1_000L) return@post
            m51LastAutoUiMs = uiNow
            m51AutoAddress = status.address
            batteryNotification.setBatteryFromBle(status)
            updateBattery()
            RootlessDiagnostics.autoBatteryUpdates.incrementAndGet()
            m51AutoExpiry?.let { manualBleHandler.removeCallbacks(it) }
            m51AutoExpiry = Runnable {
                if (manualBleAddress == null && !(isConnectedLocally && aacpReady)) {
                    batteryNotification.clearPublicBleBattery()
                    updateBattery()
                }
                m51AutoAddress = null
            }.also { manualBleHandler.postDelayed(it, 15_000L) }
        }
    }

    private fun receiveVerifiedBleBattery(status: BLEManager.AirPodsStatus) {""",
    "auto battery receiver")
service = replace_once(service,
    """            receiveManuallySelectedBleBattery(device)
            // All other public BLE broadcasts are NOT linked to a paired device.""",
    """            receiveManuallySelectedBleBattery(device)
            receiveAutomaticNearbyBattery(device, rssiDbm)
            // Unverified broadcasts are not attributed to the authenticated paired identity.""",
    "wire public BLE to display")
service = replace_once(service,
    """        manualBleResetTask?.let { manualBleHandler.removeCallbacks(it) }
        manualBleResetTask = null
        manualBleAddress = null
        clearPacketLogs()""",
    """        manualBleResetTask?.let { manualBleHandler.removeCallbacks(it) }
        m51AutoExpiry?.let { manualBleHandler.removeCallbacks(it) }
        m51AutoExpiry = null
        manualBleResetTask = null
        manualBleAddress = null
        clearPacketLogs()""",
    "cancel pending auto expiry")

battery_file = src / "composables/BatteryView.kt"
battery = replace_once(battery_file.read_text(encoding="utf-8"),
    """        Text(if (service.isConnectedLocally) "Bateria recebida pelo LibrePods"
            else "≈ BLE · passos de 10% · estojo pode manter leitura por até 30 s")""",
    """        Text(if (service.aacpReady) "Bateria pelo canal AACP"
            else "≈ BLE próximo · identidade não verificada · resolução 10%")""",
    "honest label")

audio_file = src / "composables/M51ConnectionStatus.kt"
audio = audio_file.read_text(encoding="utf-8")
audio = replace_once(audio,
    """                    if (saved != null) it.address == saved else it.name?.contains("AirPods", true) == true""",
    """                    (saved != null && it.address == saved) ||
                        it.name?.contains("AirPods", true) == true""",
    "stale saved MAC hides the real A2DP audio")
audio = replace_once(audio,"import android.os.Build\n",
    "import android.os.Build\nimport android.os.Handler\nimport android.os.Looper\n",
    "audio imports")
audio = replace_once(audio,
    "        val listener = object : BluetoothProfile.ServiceListener {",
    """        // Audio may connect after the asynchronous profile proxy callback.
        val refreshHandler = Handler(Looper.getMainLooper())
        val refreshTask = object : Runnable {
            override fun run() {
                if (!disposed) {
                    refresh()
                    refreshHandler.postDelayed(this, 3_000L)
                }
            }
        }
        refreshHandler.postDelayed(refreshTask, 3_000L)
        val listener = object : BluetoothProfile.ServiceListener {""",
    "audio live status refresh")
audio = replace_once(audio,
    "            disposed = true\n            context.unregisterReceiver(receiver)",
    "            disposed = true\n            refreshHandler.removeCallbacks(refreshTask)\n            context.unregisterReceiver(receiver)",
    "cancel refresh on screen dispose")

diag_file = src / "utils/RootlessDiagnostics.kt"
diagnostics = replace_once(diag_file.read_text(encoding="utf-8"),
    "    val rejected = AtomicInteger()\n",
    "    val rejected = AtomicInteger()\n    val autoBatteryUpdates = AtomicInteger()\n",
    "auto battery diagnostic counter")
diagnostics = replace_once(diagnostics,
    "Etapa: $controlStage\n",
    "Atualizações automáticas BLE não autenticadas: $autoBatteryUpdates\nEtapa: $controlStage\n",
    "append diagnostics")

policy_file = src / "utils/M51AutoBatteryPolicy.kt"
if policy_file.exists(): raise RuntimeError("Policy file exists; refusing overwrite")
policy = """/* LibrePods M51 extension, AGPL-3.0-or-later. Never authenticates BLE identity. */
package me.kavishdevar.librepods.utils

internal class M51AutoBatteryPolicy(
    private val freshnessMs: Long = 6_000L, private val minimumRssiDbm: Int = -85
) {
    enum class Decision { CHOSEN_SOURCE, OTHER_SOURCE, NO_BOND, WEAK_SIGNAL }
    private data class Candidate(val timeMs: Long, val rssiDbm: Int)
    private val candidates = linkedMapOf<String, Candidate>()
    private var chosenAddress: String? = null

    @Synchronized
    fun observe(address: String, rssiDbm: Int, hasBondedAirPods: Boolean, nowMs: Long): Decision {
        candidates.entries.removeAll { nowMs < it.value.timeMs ||
            nowMs - it.value.timeMs >= freshnessMs }
        if (!candidates.containsKey(chosenAddress)) chosenAddress = null
        if (address.isNotBlank() && rssiDbm >= minimumRssiDbm) {
            candidates[address] = Candidate(nowMs, rssiDbm)
        }
        if (!hasBondedAirPods) return Decision.NO_BOND
        if (address.isBlank() || rssiDbm < minimumRssiDbm) return Decision.WEAK_SIGNAL

        // Approach inspired by OpenPods' strongest-recent-advert logic,
        // reimplemented independently with 8 dBm hysteresis. Proximity is NOT identity!
        val strongest = candidates.maxByOrNull { it.value.rssiDbm } ?: return Decision.WEAK_SIGNAL
        if (chosenAddress == null) chosenAddress = strongest.key
        val selectedSignal = candidates[chosenAddress]?.rssiDbm
        if (strongest.key != chosenAddress &&
            selectedSignal != null && strongest.value.rssiDbm - selectedSignal >= 8) {
            chosenAddress = strongest.key
        }
        return if (chosenAddress == address) Decision.CHOSEN_SOURCE else Decision.OTHER_SOURCE
    }
}
"""
test_file = tests / "M51AutoBatteryPolicyTest.kt"
if test_file.exists(): raise RuntimeError("Test file exists; refusing overwrite")
test = """package me.kavishdevar.librepods.utils

import org.junit.Assert.assertEquals
import org.junit.Test

class M51AutoBatteryPolicyTest {
    @Test fun oneFreshCandidateEnablesPreview() {
        val gate = M51AutoBatteryPolicy()
        assertEquals(M51AutoBatteryPolicy.Decision.CHOSEN_SOURCE, gate.observe("A", -50, true, 1))
        assertEquals(M51AutoBatteryPolicy.Decision.CHOSEN_SOURCE, gate.observe("A", -60, true, 200))
    }
    @Test fun strongerRecentAdvertWinsWithoutPretendingIdentity() {
        val gate = M51AutoBatteryPolicy()
        gate.observe("A", -64, true, 10)
        assertEquals(M51AutoBatteryPolicy.Decision.CHOSEN_SOURCE, gate.observe("B", -50, true, 100))
        assertEquals(M51AutoBatteryPolicy.Decision.OTHER_SOURCE, gate.observe("A", -64, true, 200))
        assertEquals(M51AutoBatteryPolicy.Decision.CHOSEN_SOURCE, gate.observe("B", -50, true, 300))
    }
    @Test fun nearTieUsesHysteresisUntilOriginalSourceExpires() {
        val gate = M51AutoBatteryPolicy()
        gate.observe("A", -60, true, 0)
        assertEquals(M51AutoBatteryPolicy.Decision.OTHER_SOURCE, gate.observe("B", -56, true, 500))
        assertEquals(M51AutoBatteryPolicy.Decision.CHOSEN_SOURCE, gate.observe("A", -60, true, 1_000))
        assertEquals(M51AutoBatteryPolicy.Decision.CHOSEN_SOURCE, gate.observe("B", -56, true, 7_001))
    }
    @Test fun previewRequiresBondAndSignal() {
        val gate = M51AutoBatteryPolicy()
        assertEquals(M51AutoBatteryPolicy.Decision.NO_BOND, gate.observe("A", -55, false, 100))
        assertEquals(M51AutoBatteryPolicy.Decision.WEAK_SIGNAL, gate.observe("A", -94, true, 150))
    }
    @Test fun clocksGoingBackwardsEvictOldFrames() {
        val gate = M51AutoBatteryPolicy()
        gate.observe("A", -55, true, 9999)
        assertEquals(M51AutoBatteryPolicy.Decision.CHOSEN_SOURCE, gate.observe("B", -44, true, 1))
    }
}
"""
for file, contents in [(service_file,service),(battery_file,battery),
                       (audio_file,audio),(diag_file,diagnostics)]:
    file.write_text(contents, encoding="utf-8")
policy_file.write_text(policy, encoding="utf-8")
tests.mkdir(parents=True, exist_ok=True)
test_file.write_text(test, encoding="utf-8")
print("PASS: BLE auto-preview, short expiry, audio indicator refresh; 4 gate regression tests added")
