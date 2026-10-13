#!/usr/bin/env python3
"""Fix repeated Compose preferences registration and stale AACP badge.
Applied after prior p0-p4 patches; keeps original v4 app identity and no root.
AGPL-3.0-or-later.
"""
from pathlib import Path
import sys
if len(sys.argv)!=2: raise SystemExit("usage: python3 scripts/m51-p5-compose-state.py source/LibrePods-M51-v4")
path=Path(sys.argv[1])/"android/app/src/main/java/me/kavishdevar/librepods/MainActivity.kt"
text=path.read_text(encoding="utf-8")
def patch(old,new,label):
    global text
    count=text.count(old)
    if count!=1:raise RuntimeError(f"{label}: expected 1 match, got {count}")
    text=text.replace(old,new,1)

patch("""        val sharedPreferences = context.getSharedPreferences("settings", MODE_PRIVATE)
        val isAvailableChangeListener = SharedPreferences.OnSharedPreferenceChangeListener { _, key ->
            if (key == "CrossDeviceIsAvailable") {
                Log.d("MainActivity", "CrossDeviceIsAvailable changed")
                isRemotelyConnected.value = sharedPreferences.getBoolean("CrossDeviceIsAvailable", false)
            }
        }
        sharedPreferences.registerOnSharedPreferenceChangeListener(isAvailableChangeListener)
        Log.d("MainActivity", "CrossDeviceIsAvailable: ${sharedPreferences.getBoolean("CrossDeviceIsAvailable", false)} | isAvailable: ${CrossDevice.isAvailable}")
        isRemotelyConnected.value = sharedPreferences.getBoolean("CrossDeviceIsAvailable", false) || CrossDevice.isAvailable
        Log.d("MainActivity", "isRemotelyConnected: ${isRemotelyConnected.value}")""",
"""        val sharedPreferences = remember(context) { context.getSharedPreferences("settings", MODE_PRIVATE) }
        DisposableEffect(sharedPreferences) {
            val listener = SharedPreferences.OnSharedPreferenceChangeListener { _, key ->
                if (key == "CrossDeviceIsAvailable") {
                    isRemotelyConnected.value =
                        sharedPreferences.getBoolean("CrossDeviceIsAvailable", false) || CrossDevice.isAvailable
                }
            }
            sharedPreferences.registerOnSharedPreferenceChangeListener(listener)
            isRemotelyConnected.value =
                sharedPreferences.getBoolean("CrossDeviceIsAvailable", false) || CrossDevice.isAvailable
            onDispose { sharedPreferences.unregisterOnSharedPreferenceChangeListener(listener) }
        }""",
"preference listener Compose lifetime")

patch("""        if (airPodsService.value?.isConnectedLocally == true) {
            isConnected.value = true
        }""",
"""        // Do not latch a stale 'connected' flag after L2CAP drops. AACP readiness
        // is distinct from Bluetooth audio and BLE battery availability.
        LaunchedEffect(airPodsService.value) {
            while (true) {
                val service = airPodsService.value
                isConnected.value = service?.let { it.isConnectedLocally && it.aacpReady } == true
                kotlinx.coroutines.delay(1_000L)
            }
        }""",
"correct control channel UI state")

# The MaterialTheme color is used elsewhere; keep persistence but do it as a
# Compose effect, not a database write every time the screen recomposes.
patch("""                getSharedPreferences("settings", MODE_PRIVATE).edit().putLong("textColor",
                    MaterialTheme.colorScheme.onSurface.toArgb().toLong()).apply()
                Main()""",
"""                val color = MaterialTheme.colorScheme.onSurface.toArgb().toLong()
                LaunchedEffect(color) {
                    getSharedPreferences("settings", MODE_PRIVATE)
                        .edit().putLong("textColor", color).apply()
                }
                Main()""",
"save text theme color on changes only")

path.write_text(text,encoding="utf-8")
print("PASS: lifecycle-scoped preferences observer, AACP status refresh, theme writes only when needed")
