#!/usr/bin/env python3
"""LibrePods M51 v6: refresh user-chosen, unverified BLE battery while advertisements arrive.
Runs after the existing v5 experiment was applied in CI. Does not bypass Android L2CAP,
claim device identity, or modify AACP control packets. License: AGPL-3.0-or-later.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1]) / "android/app/src/main/java/me/kavishdevar/librepods"

def modify(relpath: str, old: str, new: str):
    p = root / relpath
    content = p.read_text(encoding="utf-8")
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f"{relpath}: expected exactly one occurrence, found {count}: {old[:120]!r}")
    p.write_text(content.replace(old, new, 1), encoding="utf-8")

# The manual preview no longer expires when the selected address still broadcasts.
# It is cleared 60 seconds after the last advertisement (including RPA rotation).
modify("services/AirPodsService.kt", """            if (status.address == manualBleAddress &&
                android.os.SystemClock.elapsedRealtime() < manualBleExpiryMs && !isConnectedLocally) {
                batteryNotification.setBatteryFromBle(status)
                updateBattery()
            }""", """            if (status.address == manualBleAddress &&
                android.os.SystemClock.elapsedRealtime() < manualBleExpiryMs && !isConnectedLocally) {
                // Renew only while this explicitly selected address broadcasts.
                manualBleExpiryMs = android.os.SystemClock.elapsedRealtime() + 60_000L
                manualBleResetTask?.let { task ->
                    manualBleHandler.removeCallbacks(task)
                    manualBleHandler.postDelayed(task, 60_000L)
                }
                batteryNotification.setBatteryFromBle(status)
                updateBattery()
            }""")

# A single explicit tap can choose the only nearby Pro 3 BLE announcement.
# Multiple nearby devices require the user to select one manually.
modify("screens/Onboarding.kt", """  }) { Text("Mostrar bateria BLE selecionada na tela principal · 60 s") }""", """  }) { Text("Mostrar bateria BLE selecionada na tela principal · 60 s") }
  OutlinedButton(onClick = {
      val candidatesPro3 = RootlessDiagnostics.devices().filter { it.second.contains("AirPods Pro 3") }
      if (candidatesPro3.size == 1) {
          RootlessDiagnostics.selected = candidatesPro3.single().first
          val displayed = ServiceManager.getService()?.displaySelectedBleBattery() == true
          RootlessDiagnostics.stage(if (displayed)
              "Bateria BLE ativada. Atualiza enquanto o mesmo anúncio for recebido; " +
                  "desaparece 60 s depois do último anúncio. Identidade não verificada."
              else "Não foi possível exibir a bateria. Reconecte os fones e repita a busca BLE.")
      } else {
          RootlessDiagnostics.stage(if (candidatesPro3.isEmpty())
              "Nenhum anúncio AirPods Pro 3 encontrado. Abra o estojo, reinicie a busca e tente de novo."
              else "Há vários anúncios AirPods Pro 3. Escolha manualmente o correto na lista acima.")
      }
      revision++
  }) { Text("Usar único AirPods Pro 3 próximo · bateria BLE") }
  Text("M51 sem root: a bateria BLE pode funcionar sem L2CAP. Os modos " +
       "Cancelamento, Transparência e Adaptativo pelo aplicativo exigem conexão " +
       "AACP/L2CAP, que pode falhar no Android 12. Nenhum anúncio BLE prova, sozinho, " +
       "ser dos seus AirPods. A leitura é aproximada e só é mostrada quando recente.")""")

print("PASS: M51 v6 continuous opt-in BLE preview and one-touch single-candidate selector")
