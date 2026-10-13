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

# The packaged M51 v4 source has permission-dependent Compose UI, not the
# upstream newer onboardingComplete state. Do not change the permissions flow.
connection_pattern = re.compile(
    r"(?m)^\s*serviceConnection = remember \{.*?^\s*context\.bindService\(Intent\(context, AirPodsService::class\.java\), serviceConnection, Context\.BIND_AUTO_CREATE\)",
    re.DOTALL | re.MULTILINE,
)
connection_replacement = """
        val m51ServiceConnection = remember(context) {
            object : ServiceConnection {
                override fun onServiceConnected(name: ComponentName?, binder: IBinder?) {
                    airPodsService.value = (binder as? AirPodsService.LocalBinder)?.getService()
                }

                override fun onServiceDisconnected(name: ComponentName?) {
                    airPodsService.value = null
                }
            }
        }

        // Bind only while the permissions-granted screen is composed, not at
        // every redraw. Preserve the original LibrePods service and AACP.
        DisposableEffect(context, m51ServiceConnection) {
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
            val btFilter = android.content.IntentFilter(android.bluetooth.BluetoothAdapter.ACTION_STATE_CHANGED)
            if (android.os.Build.VERSION.SDK_INT >= 33) {
                context.registerReceiver(bluetoothReceiver, btFilter, Context.RECEIVER_EXPORTED)
            } else {
                context.registerReceiver(bluetoothReceiver, btFilter)
            }
            val bound = try {
                context.bindService(
                    Intent(context, AirPodsService::class.java),
                    m51ServiceConnection,
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
                    try { context.unbindService(m51ServiceConnection) }
                    catch (_: IllegalArgumentException) { }
                }
                airPodsService.value = null
            }
        }"""
source, count = connection_pattern.subn(lambda _: connection_replacement, source)
if count != 1:
    raise RuntimeError(f"M51 v4 binding block: expected exactly one, found {count}")

main.write_text(source, encoding="utf-8")

gradle_text = gradle.read_text(encoding="utf-8")
gradle_text = exactly_one_replace(gradle_text, "versionCode = 17", "versionCode = 18", "versionCode")
gradle_text = exactly_one_replace(
    gradle_text, 'versionName = "0.1.0-rc.4-m51-v7"',
    'versionName = "0.1.0-rc.4-m51-v8"', "versionName"
)
gradle.write_text(gradle_text, encoding="utf-8")
print("PASS: v8 one-time service binding; guarded unbind; BLE retry on Bluetooth STATE_ON; version 18")
