#!/usr/bin/env python3
"""Show BLE counters and copyable diagnostic on the main screen without L2CAP."""
from pathlib import Path
import sys
if len(sys.argv) != 2:
    raise SystemExit("usage: python3 scripts/m51-p2-visible-diagnostics.py source/LibrePods-M51-v4")
root = Path(sys.argv[1]) / "android/app/src/main/java/me/kavishdevar/librepods"
ui = root / "screens/AirPodsSettingsScreen.kt"
widget = root / "composables/M51DiagnosticSnapshot.kt"
if widget.exists(): raise RuntimeError("Refusing to overwrite existing diagnostic widget")
source = ui.read_text(encoding="utf-8")
replacements = [
(
"""                BatteryView(service = service)
                // The public BLE estimate is deliberately separate from authenticated AACP data.""",
"""                BatteryView(service = service)
                me.kavishdevar.librepods.composables.M51DiagnosticSnapshot()
                // The public BLE estimate is deliberately separate from authenticated AACP data."""
),
(
"""                BatteryView(service = service)
                Text(
                    text = "Áudio e bateria BLE funcionam por canais separados.""",
"""                BatteryView(service = service)
                me.kavishdevar.librepods.composables.M51DiagnosticSnapshot()
                Text(
                    text = "Áudio e bateria BLE funcionam por canais separados."""
)
]
for old, new in replacements:
    if source.count(old) != 1: raise RuntimeError("main screen anchor missing or repeated")
    source = source.replace(old, new, 1)
widget_source = """/* LibrePods M51 extension, AGPL-3.0-or-later.
 * Main-screen BLE diagnostic; no navigation or working L2CAP required.
 */
package me.kavishdevar.librepods.composables

import android.content.ClipData
import android.content.ClipboardManager
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay
import me.kavishdevar.librepods.utils.RootlessDiagnostics

@Composable
fun M51DiagnosticSnapshot() {
    val context = LocalContext.current
    var revision by remember { mutableIntStateOf(0) }
    var feedback by remember { mutableStateOf("") }
    LaunchedEffect(Unit) {
        while (true) { delay(1_500L); revision++ }
    }
    val report = remember(revision) { RootlessDiagnostics.report() }
    val counts = remember(revision) {
        "BLE: ${RootlessDiagnostics.total.get()} · Apple: ${RootlessDiagnostics.apple.get()} · Proximidade: ${RootlessDiagnostics.proximity.get()}"
    }
    val scanState = remember(revision) { RootlessDiagnostics.scanStatus }
    Column(
        modifier = Modifier.fillMaxWidth().padding(vertical = 10.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text("Diagnóstico BLE (sem root)", fontSize = 14.sp)
        Text(counts, fontSize = 12.sp)
        Text(scanState, fontSize = 12.sp)
        Button(onClick = {
            try {
                val clipboard = context.getSystemService(ClipboardManager::class.java)
                if (clipboard == null) {
                    feedback = "Área de transferência indisponível"
                } else {
                    clipboard.setPrimaryClip(ClipData.newPlainText("LibrePods M51", report))
                    feedback = "Diagnóstico copiado"
                }
            } catch (_: Exception) {
                feedback = "Não foi possível copiar"
            }
        }) { Text("Copiar diagnóstico", fontSize = 14.sp) }
        if (feedback.isNotEmpty()) Text(feedback, fontSize = 12.sp)
    }
}
"""
ui.write_text(source, encoding="utf-8")
widget.write_text(widget_source, encoding="utf-8")
print("PASS: main screen BLE counters and clipboard report available in both AACP states")
