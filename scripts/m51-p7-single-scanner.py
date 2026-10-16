#!/usr/bin/env python3
"""Prevent parallel BLE scan registrations when Android 12 fallback restarts a scan.

Runs after p4-p6. Works on the existing LibrePods source; does not add an app,
enable AACP, request root, or generate an APK for distribution.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: python3 scripts/m51-p7-single-scanner.py source/LibrePods-M51-v4")

file = Path(sys.argv[1]) / "android/app/src/main/java/me/kavishdevar/librepods/utils/BLEManager.kt"
source = file.read_text(encoding="utf-8")
anchor = """        cleanupHandler.removeCallbacks(cleanupRunnable)
        try {
            Log.d(TAG, "Starting BLE scanner")"""
replacement = """        cleanupHandler.removeCallbacks(cleanupRunnable)
        // The 25-second manufacturer-filter fallback and Bluetooth recovery call
        // startScanning() again. Before assigning a NEW ScanCallback, unregister
        // the old one. Otherwise stopScanning() only knows about the latest
        // callback, leaving an orphaned scan active in the Android stack.
        val previousCallback = mScanCallback
        if (previousCallback != null) {
            try {
                mBluetoothLeScanner?.stopScan(previousCallback)
            } catch (e: SecurityException) {
                RootlessDiagnostics.scanStatus = "Permissão Bluetooth necessária para reiniciar a busca BLE"
                Log.w(TAG, "Could not stop previous BLE scan: missing permission", e)
                return
            } catch (e: Exception) {
                RootlessDiagnostics.scanStatus = "Falha ao encerrar busca BLE anterior; nova busca não iniciada"
                Log.w(TAG, "Could not stop previous BLE scan; refusing duplicate registration", e)
                return
            }
            mScanCallback = null
        }
        try {
            Log.d(TAG, "Starting BLE scanner")"""
if source.count(anchor) != 1:
    raise RuntimeError(f"BLE scanner start anchor expected once, found {source.count(anchor)}")
if source.count("fun startScanning(unfiltered: Boolean = false)") != 1:
    raise RuntimeError("Unexpected BLE scanner implementation, refusing patch")
if source.count("private var mScanCallback: ScanCallback? = null") != 1:
    raise RuntimeError("Unexpected callback storage, refusing patch")
source = source.replace(anchor, replacement, 1)
file.write_text(source, encoding="utf-8")
print("PASS: every BLE scan restart stops previous ScanCallback before registering another")
