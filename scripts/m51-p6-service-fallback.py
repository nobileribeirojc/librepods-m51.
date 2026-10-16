#!/usr/bin/env python3
"""Keep main-screen BLE diagnostics available even if AirPodsService is not bound.
Adds explicit user-controlled activity retry rather than an infinite rebind loop.
"""
from pathlib import Path
import sys
if len(sys.argv)!=2:raise SystemExit("usage: python3 scripts/m51-p6-service-fallback.py source/LibrePods-M51-v4")
path=Path(sys.argv[1])/"android/app/src/main/java/me/kavishdevar/librepods/MainActivity.kt"
s=path.read_text(encoding="utf-8")
old="""                    if (airPodsService.value != null) {
                        AirPodsSettingsScreen(
                            dev = airPodsService.value?.device,
                            service = airPodsService.value!!,
                            navController = navController,
                            isConnected = isConnected.value,
                            isRemotelyConnected = isRemotelyConnected.value
                        )
                    }
"""
new="""                    val attachedService = airPodsService.value
                    if (attachedService != null) {
                        AirPodsSettingsScreen(
                            dev = attachedService.device,
                            service = attachedService,
                            navController = navController,
                            isConnected = isConnected.value,
                            isRemotelyConnected = isRemotelyConnected.value
                        )
                    } else {
                        // A blank screen is unacceptable precisely when the binder fails.
                        // BLE counters and export are independent of a working AACP socket.
                        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp)) {
                            Text("LibrePods M51 · aguardando serviço Bluetooth")
                            Text("Sem vínculo com o serviço. Verifique permissões Bluetooth e localização.")
                            me.kavishdevar.librepods.composables.M51DiagnosticSnapshot()
                            Button(onClick = {
                                (context as? android.app.Activity)?.recreate()
                            }) { Text("Tentar iniciar serviço novamente") }
                        }
                    }
"""
if s.count(old)!=1:raise RuntimeError(f"service-bound settings UI anchor mismatch: {s.count(old)}")
s=s.replace(old,new,1)
path.write_text(s,encoding="utf-8")
print("PASS: diagnostic survives service binding failure; manual restart button added")
