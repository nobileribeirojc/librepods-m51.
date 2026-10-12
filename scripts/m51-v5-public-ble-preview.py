#!/usr/bin/env python3
"""LibrePods M51 experimental no-root BLE preview. AGPL-3.0-or-later."""
from pathlib import Path
import sys
src = Path(sys.argv[1]) / "android/app/src/main/java/me/kavishdevar/librepods"
def change(f, old, new):
    p = src/f
    s = p.read_text(encoding="utf8")
    n = s.count(old)
    if n != 1:
        raise RuntimeError(f"{f}: expected one source anchor, got {n}: {old[:90]}")
    p.write_text(s.replace(old, new, 1), encoding="utf8")

change("utils/Packets.kt",
    "        fun setBattery(data: ByteArray) {",
    """        /** Reset the explicit public BLE preview to unknown, not to 0%. */
        fun clearPublicBleBattery() {
            first = Battery(BatteryComponent.LEFT, 0, BatteryStatus.DISCONNECTED)
            second = Battery(BatteryComponent.RIGHT, 0, BatteryStatus.DISCONNECTED)
            case = Battery(BatteryComponent.CASE, 0, BatteryStatus.DISCONNECTED)
        }

        fun setBattery(data: ByteArray) {""")

change("services/AirPodsService.kt",
    "    private var popupAddressM51: String? = null",
    """    private var popupAddressM51: String? = null

    // RPA addresses rotate: never treat public BLE as verified identity.
    @Volatile private var manualBleAddress: String? = null
    @Volatile private var manualBleExpiryMs: Long = 0L
    private val manualBleHandler = Handler(Looper.getMainLooper())
    private var manualBleResetTask: Runnable? = null

    /** One selected public BLE candidate, for sixty seconds only; no pairing claim. */
    fun displaySelectedBleBattery(): Boolean {
        val candidate = RootlessDiagnostics.selectedStatus() ?: return false
        if (isConnectedLocally || candidate.model != "AirPods Pro 3") return false
        val now = android.os.SystemClock.elapsedRealtime()
        manualBleAddress = candidate.address
        manualBleExpiryMs = now + 60_000L
        batteryNotification.setBatteryFromBle(candidate)
        updateBattery()
        manualBleResetTask?.let { manualBleHandler.removeCallbacks(it) }
        manualBleResetTask = Runnable {
            manualBleAddress = null
            manualBleExpiryMs = 0L
            if (!isConnectedLocally) {
                batteryNotification.clearPublicBleBattery()
                updateBattery()
            }
        }.also { manualBleHandler.postDelayed(it, 60_000L) }
        return true
    }

    private fun receiveManuallySelectedBleBattery(status: BLEManager.AirPodsStatus) {
        if (status.address != manualBleAddress ||
            android.os.SystemClock.elapsedRealtime() >= manualBleExpiryMs) return
        manualBleHandler.post {
            if (status.address == manualBleAddress &&
                android.os.SystemClock.elapsedRealtime() < manualBleExpiryMs && !isConnectedLocally) {
                batteryNotification.setBatteryFromBle(status)
                updateBattery()
            }
        }
    }""")

change("services/AirPodsService.kt",
    """        override fun onNearbyProximityAdvertisement(device: BLEManager.AirPodsStatus, rssiDbm: Int) {
            // This is an UNVERIFIED public advertisement, never alter the trusted
            // battery notification or infer that it came from the paired AirPods.""",
    """        override fun onNearbyProximityAdvertisement(device: BLEManager.AirPodsStatus, rssiDbm: Int) {
            // Only an explicitly selected short-lived public BLE address is shown.
            receiveManuallySelectedBleBattery(device)
            // All other public BLE broadcasts are NOT linked to a paired device.""")

change("services/AirPodsService.kt",
    """    override fun onDestroy() {
        clearPacketLogs()""",
    """    override fun onDestroy() {
        manualBleResetTask?.let { manualBleHandler.removeCallbacks(it) }
        manualBleResetTask = null
        manualBleAddress = null
        clearPacketLogs()""")

change("screens/Onboarding.kt",
    """  Text("Se o teste falhar, compartilhe o relatório abaixo. Não mostra endereço Bluetooth, " +""",
    """  OutlinedButton(onClick = {
      ServiceManager.getService()?.bleManager?.startScanning()
      revision++
  }) { Text("Reiniciar busca BLE (abra o estojo)") }
  Text("Se o teste falhar, compartilhe o relatório abaixo. Não mostra endereço Bluetooth, " +""")

change("screens/Onboarding.kt",
    """  candidates.forEach { item -> OutlinedButton(onClick = { RootlessDiagnostics.selected = item.first; revision++ }) { Text(item.second) } }""",
    """  candidates.forEach { item -> OutlinedButton(onClick = { RootlessDiagnostics.selected = item.first; revision++ }) { Text(item.second) } }
  Text("Bateria BLE na tela principal (teste manual)", style = MaterialTheme.typography.titleMedium)
  Text("Selecione um anúncio recente. O BLE público não autentica a identidade: " +
       "pode ser de outro aparelho próximo. Bateria aproximada por 60 segundos; " +
       "não muda os controles de ruído.")
  Button(enabled = RootlessDiagnostics.selectedStatus() != null, onClick = {
      val service = ServiceManager.getService()
      val success = service?.displaySelectedBleBattery() == true
      RootlessDiagnostics.stage(if (success) "Bateria pública BLE exibida por 60 s (não autenticada)"
          else "Selecione anúncio recente dos AirPods Pro 3; prévia indisponível")
      revision++
  }) { Text("Mostrar bateria BLE selecionada na tela principal · 60 s") }""")

print("PASS: manual candidate, battery preview, 60 s expiry, scanner restart, no root")
