#!/usr/bin/env python3
"""LibrePods M51 v9: avoid false BLE scan cooldown; remember BT-on while service binds.
Runs AFTER the v8 lifecycle script, and only on its exact Kotlin anchors.
AGPL-3.0-or-later. Platform Bluetooth restrictions remain unchanged.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: python3 scripts/m51-v9-ble-recovery.py source/LibrePods-M51-v4")

base = Path(sys.argv[1]) / "android/app"
root = base / "src/main/java/me/kavishdevar/librepods"
ble_path = root / "utils/BLEManager.kt"
main_path = root / "MainActivity.kt"
gradle_path = base / "build.gradle.kts"

def replace_exact(source: str, before: str, after: str, label: str) -> str:
    occurrences = source.count(before)
    if occurrences != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {occurrences}")
    return source.replace(before, after, 1)

# Purely local BLE guard: an adapter that is OFF/null, or an exception from startScan(),
# must not start the six-second cooldown. Calling ?.startScan() previously recorded a
# start even when the nullable scanner was absent.
ble = ble_path.read_text(encoding="utf-8")
ble = replace_exact(ble,
    """        lastScanStartMs = now
        cleanupHandler.removeCallbacks(cleanupRunnable)""",
    """        cleanupHandler.removeCallbacks(cleanupRunnable)""",
    "do not stamp failed BLE attempts")
ble = replace_exact(ble,
    """            mBluetoothLeScanner?.startScan(if (unfiltered) emptyList() else listOf(scanFilter), scanSettings, mScanCallback)
            RootlessDiagnostics.scanStatus = if (unfiltered) "BLE sem filtro (teste com tela acesa)" else "BLE com filtro Apple ativo" """.rstrip(),
    """            val scanner = mBluetoothLeScanner
            if (scanner == null) {
                RootlessDiagnostics.scanStatus = "Scanner BLE indisponível: Bluetooth desligado ou sem permissão"
                Log.w(TAG, "BLE scan not started: scanner unavailable")
                return
            }
            scanner.startScan(if (unfiltered) emptyList() else listOf(scanFilter), scanSettings, mScanCallback)
            // Record the cooldown only after the Android scanner accepted startScan.
            lastScanStartMs = android.os.SystemClock.elapsedRealtime()
            RootlessDiagnostics.scanStatus = if (unfiltered) "BLE sem filtro (teste com tela acesa)" else "BLE com filtro Apple ativo" """.rstrip(),
    "BLE scanner accepted start")
# Keep all outputs in memory until the v9 anchors have been validated.

main = main_path.read_text(encoding="utf-8")
main = replace_exact(main,
    """        val m51ServiceConnection = remember(context) {""",
    """        // Bluetooth may turn ON before the asynchronous service binder is ready.
        // Preserve one pending restart instead of silently dropping the event.
        val m51PendingBleRestart = remember { java.util.concurrent.atomic.AtomicBoolean(false) }
        val m51ServiceConnection = remember(context) {""",
    "pending-restart guard")
main = replace_exact(main,
    """                    airPodsService.value = (binder as? AirPodsService.LocalBinder)?.getService()
                }

                override fun onServiceDisconnected""",
    """                    airPodsService.value = (binder as? AirPodsService.LocalBinder)?.getService()
                    if (m51PendingBleRestart.getAndSet(false)) {
                        airPodsService.value?.bleManager?.startScanning()
                    }
                }

                override fun onServiceDisconnected""",
    "service-binding scan recovery")
main = replace_exact(main,
    """                        airPodsService.value?.bleManager?.startScanning()
                    }
                }
            }
            val btFilter""",
    """                        val currentService = airPodsService.value
                        if (currentService == null) {
                            m51PendingBleRestart.set(true)
                        } else {
                            currentService.bleManager?.startScanning()
                        }
                    }
                }
            }
            val btFilter""",
    "BT ON pending reconnect")

gradle = gradle_path.read_text(encoding="utf-8")
gradle = replace_exact(gradle,
    "versionCode = 18",
    "versionCode = 19",
    "v9 versionCode")
gradle = replace_exact(gradle,
    'versionName = "0.1.0-rc.4-m51-v8"',
    'versionName = "0.1.0-rc.4-m51-v9-ble-recovery"',
    "v9 versionName")

# All anchors matched, so commit the edits.
ble_path.write_text(ble, encoding="utf-8")
main_path.write_text(main, encoding="utf-8")
gradle_path.write_text(gradle, encoding="utf-8")
print("PASS: v9 BLE cooldown only after startScan, deferred scan retry after service bind, version 19")
