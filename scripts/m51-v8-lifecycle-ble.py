#!/usr/bin/env python3
"""LibrePods M51 v8: bind Android service once per Compose lifetime, retry BLE on BT ON.
Applies AFTER scripts/m51-v7.patch to the original LibrePods Android source.
AGPL-3.0-or-later. Does not bypass or claim to repair AACP/L2CAP.
"""
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: python3 scripts/m51-v8-lifecycle-ble.py source/LibrePods-M51-v4")

base = Path(sys.argv[1]) / "android/app"
main = base / "src/main/java/me/kavishdevar/librepods/MainActivity.kt"
gradle = base / "build.gradle.kts"


def exactly_one_replace(text: str, before: str, after: str, label: str) -> str:
    count = text.count(before)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one occurrence, found {count}")
    return text.replace(before, after, 1)


source = main.read_text(encoding="utf-8")
print("M51_MAIN_LINES", "\n".join(f"{i+1:03d} {line}" for i,line in enumerate(source.splitlines()) if (i<55 or 260<=i<372)))
print("M51_BASE_ANCHORS", [(i, line.strip()[:120]) for i, line in enumerate(source.splitlines(), 1) if any(k in line for k in ["onboardingComplete", "onboarding_complete", "fun bindService", "bindService()", "showOnboarding", "NavigationRoot", "serviceConnection", "connectionStatusReceiver"])])
# The legacy code unbound in onStop AND onDestroy, even before lateinit initialization,
# and re-bound on each Compose recomposition. This matches the M51 logcat.
pattern = re.compile(
    r"    override fun onDestroy\(\) \{.*?\n    override fun onStop\(\) \{.*?\n    \}\n\}",
    re.DOTALL,
)
replacement = """    override fun onDestroy() {
        // The composition's DisposableEffect owns bind/unbind; onStop must not
        // tear it down while the Activity is merely in the background.
        sendBroadcast(Intent(AirPodsNotifications.DISCONNECT_RECEIVERS))
        super.onDestroy()
    }
}"""
source, changed = pattern.subn(replacement, source)
if changed != 1:
    raise RuntimeError(f"MainActivity lifecycle methods: expected one block, found {changed}")

source = exactly_one_replace(
    source,
    '    val onboardingComplete = sharedPreferences.getBoolean("onboarding_complete", false)',
    '    val onboardingComplete = remember { mutableStateOf(sharedPreferences.getBoolean("onboarding_complete", false)) }',
    "reactive onboarding flag",
)

# Move service ownership to the composition lifecycle, not its render function.
# Keep all original service/ViewModel initialization, including the initial time record.
start_marker = "    fun bindService() {"
end_marker = "    NavigationRoot("
first = source.find(start_marker)
last = source.find(end_marker, first)
if first < 0 or last < 0 or source.count(start_marker) != 1:
    raise RuntimeError("Cannot identify unique legacy binding block")
old_block = source[first:last]
if 'if (onboardingComplete)' not in old_block or 'context.bindService(' not in old_block:
    raise RuntimeError("Legacy binding block has changed; refusing unsafe patch")

new_block = """    DisposableEffect(context, onboardingComplete.value) {
        if (!onboardingComplete.value) {
            onDispose { }
        } else {
            context.startForegroundService(Intent(context, AirPodsService::class.java))
            val connection = object : ServiceConnection {
                override fun onServiceConnected(name: ComponentName?, binder: IBinder?) {
                    val connected = (binder as? AirPodsService.LocalBinder)?.getService() ?: return
                    airPodsService.value = connected
                    airPodsViewModel.init(
                        service = connected,
                        controlRepo = ControlCommandRepository(connected.aacpManager),
                        sharedPreferences = context.getSharedPreferences("settings", MODE_PRIVATE),
                        appContext = context.applicationContext
                    )
                    if (!sharedPreferences.contains("first_connection_successful_time")) {
                        sharedPreferences.edit {
                            putLong("first_connection_successful_time", System.currentTimeMillis())
                        }
                    }
                }

                override fun onServiceDisconnected(name: ComponentName?) {
                    airPodsService.value = null
                }
            }

            // M51 log: the first scan occurred while Bluetooth was disabled.
            // Re-start public BLE when Android subsequently reports STATE_ON.
            // This listener is independent of the failing classic L2CAP/AACP channel.
            val bluetoothReceiver = object : BroadcastReceiver() {
                override fun onReceive(receiverContext: Context?, intent: Intent?) {
                    if (intent?.action == android.bluetooth.BluetoothAdapter.ACTION_STATE_CHANGED &&
                        intent.getIntExtra(
                            android.bluetooth.BluetoothAdapter.EXTRA_STATE,
                            android.bluetooth.BluetoothAdapter.ERROR
                        ) == android.bluetooth.BluetoothAdapter.STATE_ON
                    ) {
                        airPodsService.value?.bleManager?.startScanning()
                    }
                }
            }
            val filter = android.content.IntentFilter(android.bluetooth.BluetoothAdapter.ACTION_STATE_CHANGED)
            if (android.os.Build.VERSION.SDK_INT >= 33) {
                context.registerReceiver(bluetoothReceiver, filter, Context.RECEIVER_EXPORTED)
            } else {
                context.registerReceiver(bluetoothReceiver, filter)
            }
            val bound = try {
                context.bindService(
                    Intent(context, AirPodsService::class.java),
                    connection,
                    Context.BIND_AUTO_CREATE
                )
            } catch (e: Exception) {
                android.util.Log.w("MainActivity", "Unable to bind AirPodsService", e)
                false
            }
            onDispose {
                try { context.unregisterReceiver(bluetoothReceiver) }
                catch (_: IllegalArgumentException) { }
                if (bound) {
                    try { context.unbindService(connection) }
                    catch (_: IllegalArgumentException) { }
                }
                airPodsService.value = null
            }
        }
    }

"""
source = source[:first] + new_block + source[last:]
source = exactly_one_replace(
    source,
    'showOnboarding = !onboardingComplete,',
    'showOnboarding = !onboardingComplete.value,',
    "showOnboarding state",
)
source = exactly_one_replace(
    source,
    'sharedPreferences.edit { putBoolean("onboarding_complete", true) }\n            bindService()',
    'sharedPreferences.edit { putBoolean("onboarding_complete", true) }\n            onboardingComplete.value = true',
    "onboarding callback",
)
main.write_text(source, encoding="utf-8")

gradle_text = gradle.read_text(encoding="utf-8")
gradle_text = exactly_one_replace(gradle_text, "versionCode = 17", "versionCode = 18", "versionCode")
gradle_text = exactly_one_replace(
    gradle_text, 'versionName = "0.1.0-rc.4-m51-v7"',
    'versionName = "0.1.0-rc.4-m51-v8"', "versionName"
)
gradle.write_text(gradle_text, encoding="utf-8")
print("PASS: v8 one-time service binding; guarded unbind; BLE retry on Bluetooth STATE_ON; version 18")
