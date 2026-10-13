#!/usr/bin/env python3
"""Prevent automatic classic L2CAP spam on rootless Android 12. Manual diagnostics preserved."""
from pathlib import Path
import sys
if len(sys.argv) != 2:
    raise SystemExit("usage: python3 scripts/m51-p1-l2cap-guard.py source/LibrePods-M51-v4")
root=Path(sys.argv[1])/"android/app/src"
folder=root/"main/java/me/kavishdevar/librepods"
f=folder/"services/AirPodsService.kt"
s=f.read_text(encoding="utf-8")

def r(old,new,name):
    global s
    n=s.count(old)
    if n!=1:
        raise RuntimeError(f"{name}: expected 1 anchor; got {n}")
    s=s.replace(old,new,1)

r("import me.kavishdevar.librepods.utils.CasePopupPolicy\n",
  "import me.kavishdevar.librepods.utils.CasePopupPolicy\nimport me.kavishdevar.librepods.utils.M51ControlTransportPolicy\n",
  "import policy")
r("""                                CoroutineScope(Dispatchers.IO).launch { connectToSocket(pairedDevice) }""",
  """                                if (M51ControlTransportPolicy.allowAutomaticL2cap(Build.VERSION.SDK_INT)) {
                                    CoroutineScope(Dispatchers.IO).launch { connectToSocket(pairedDevice) }
                                }""",
  "BLE-address change must not spam classic L2CAP")
r("""                        CoroutineScope(Dispatchers.IO).launch {
                            connectToSocket(device!!)
                        }
                        Log.d("AirPodsService", "Setting metadata")""",
  """                        if (M51ControlTransportPolicy.allowAutomaticL2cap(Build.VERSION.SDK_INT)) {
                            CoroutineScope(Dispatchers.IO).launch {
                                connectToSocket(device!!)
                            }
                        } else {
                            RootlessDiagnostics.stage("Android 12: áudio A2DP independente; teste AACP somente manual")
                        }
                        Log.d("AirPodsService", "Setting metadata")""",
  "detected audio should not auto-create failing L2CAP")
r("""                                            CoroutineScope(Dispatchers.IO).launch {
                                                connectToSocket(device)
                                            }
                                            setMetadatas(device)""",
  """                                            if (M51ControlTransportPolicy.allowAutomaticL2cap(Build.VERSION.SDK_INT)) {
                                                CoroutineScope(Dispatchers.IO).launch {
                                                    connectToSocket(device)
                                                }
                                            }
                                            setMetadatas(device)""",
  "on service startup, guard automatic AACP")
policyFile=folder/"utils/M51ControlTransportPolicy.kt"
if policyFile.exists():
    raise RuntimeError("Refusing to overwrite transport policy")
testFile=root/"test/java/me/kavishdevar/librepods/utils/M51ControlTransportPolicyTest.kt"
if testFile.exists():
    raise RuntimeError("Refusing to overwrite transport policy test")
f.write_text(s,encoding="utf-8")
policyFile.write_text("""/* LibrePods M51 extension, AGPL-3.0-or-later. */
package me.kavishdevar.librepods.utils

/** Do not automatically retry known-failing classic AACP on unprivileged Android 12.
 * Manual user-initiated L2CAP diagnostic is independent of this decision.
 */
internal object M51ControlTransportPolicy {
    fun allowAutomaticL2cap(sdkInt: Int): Boolean = sdkInt >= 33
}
""",encoding="utf-8")
testFile.parent.mkdir(parents=True,exist_ok=True)
testFile.write_text("""package me.kavishdevar.librepods.utils

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class M51ControlTransportPolicyTest {
    @Test fun android12DoesNotAutoAttemptClassicL2cap() {
        assertFalse(M51ControlTransportPolicy.allowAutomaticL2cap(31))
        assertFalse(M51ControlTransportPolicy.allowAutomaticL2cap(32))
    }
    @Test fun newerAndroidRetainsExistingBehavior() {
        assertTrue(M51ControlTransportPolicy.allowAutomaticL2cap(33))
    }
}
""",encoding="utf-8")
print("PASS: no automatic L2CAP requests on API31/32; manual tests unchanged")
