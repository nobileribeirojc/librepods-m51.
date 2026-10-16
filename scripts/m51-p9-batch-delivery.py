#!/usr/bin/env python3
"""Apply after p8: M51/API31 controller batching with a cancellable flush pump."""
from pathlib import Path
import sys

base = Path(sys.argv[1]) / 'android/app/src'
main = base / 'main/java/me/kavishdevar/librepods'
ble_path = main / 'utils/BLEManager.kt'
ble = ble_path.read_text(encoding='utf-8')

def edit(old, new):
    global ble
    if ble.count(old) != 1:
        raise RuntimeError(f'Expected one p8 anchor: {old[:90]!r}')
    ble = ble.replace(old, new, 1)

edit('    private val cleanupHandler = Handler(Looper.getMainLooper())', '''    private val cleanupHandler = Handler(Looper.getMainLooper())
    private val m51BatchDelivery = M51BatchScanPolicy.enabled(
        android.os.Build.VERSION.SDK_INT, android.os.Build.MANUFACTURER, android.os.Build.MODEL)
    private val m51BatchPump = M51BatchScanPump(
        schedule = { task, delay -> cleanupHandler.postDelayed(task, delay); Unit },
        cancel = { cleanupHandler.removeCallbacks(it) },
        onFailure = { error ->
            RootlessDiagnostics.scanStatus = "Falha na entrega BLE em lotes; reinicie a busca após verificar Bluetooth/permissões"
            Log.w(TAG, "M51 batch flush stopped; no automatic flush retry", error)
        }
    )''')
edit('        if (!automaticRetry) m51ScanPolicy.reset()',
     '        m51BatchPump.stop()\n        if (!automaticRetry) m51ScanPolicy.reset()')
edit('        m51StoppedByUser = true', '        m51BatchPump.stop()\n        m51StoppedByUser = true')
edit('                    mScanCallback = null\n                    cleanupHandler.removeCallbacks(cleanupRunnable)',
     '                    m51BatchPump.stop()\n                    mScanCallback = null\n                    cleanupHandler.removeCallbacks(cleanupRunnable)')
edit('.setScanMode(if (unfiltered) ScanSettings.SCAN_MODE_BALANCED else ScanSettings.SCAN_MODE_LOW_LATENCY)',
     '.setScanMode(if (unfiltered && !m51BatchDelivery) ScanSettings.SCAN_MODE_BALANCED else ScanSettings.SCAN_MODE_LOW_LATENCY)')
edit('.setReportDelay(0L)', '.setReportDelay(if (m51BatchDelivery) M51BatchScanPolicy.REPORT_DELAY_MS else 0L)')
edit('''            val scanFilter = ScanFilter.Builder()
                .setManufacturerData(76, byteArrayOf()).build()''', '''            val scanFilter = if (m51BatchDelivery) {
                // A nonempty wildcard manufacturer mask was used in the physical replay.
                ScanFilter.Builder().setManufacturerData(76, byteArrayOf(0), byteArrayOf(0)).build()
            } else {
                ScanFilter.Builder().setManufacturerData(76, byteArrayOf()).build()
            }''')
edit('''                    for (result in results) {
                        processScanResult(result)''', '''                    for (result in results) {
                        if (m51BatchDelivery && !M51BatchScanPolicy.isFresh(
                                result.timestampNanos, android.os.SystemClock.elapsedRealtimeNanos())) {
                            RootlessDiagnostics.staleBatchResults.incrementAndGet()
                            continue
                        }
                        processScanResult(result)''')
edit('            scanner.startScan(if (unfiltered) emptyList() else listOf(scanFilter), scanSettings, mScanCallback)',
     '''            val activeCallback = requireNotNull(mScanCallback)
            scanner.startScan(if (unfiltered && !m51BatchDelivery) emptyList() else listOf(scanFilter), scanSettings, activeCallback)
            if (m51BatchDelivery && mScanCallback === activeCallback) {
                m51BatchPump.start(
                    isCurrent = { !m51StoppedByUser && mScanCallback === activeCallback && mBluetoothLeScanner === scanner },
                    flush = { scanner.flushPendingScanResults(activeCallback) }
                )
            }''')
edit('''            RootlessDiagnostics.scanStatus = if (unfiltered) "BLE sem filtro (fallback Samsung; tela acesa)" else "BLE com filtro Apple ativo"
            if (!unfiltered) {''', '''            RootlessDiagnostics.scanStatus = if (m51BatchDelivery)
                "BLE Samsung em lotes (5 s); entrega solicitada a cada 2 s"
            else if (unfiltered) "BLE sem filtro (fallback Samsung; tela acesa)" else "BLE com filtro Apple ativo"
            if (!unfiltered && !m51BatchDelivery) {''')
edit('''        } catch (t: Throwable) {
            RootlessDiagnostics.scanStatus = "Erro BLE:''', '''        } catch (t: Throwable) {
            m51BatchPump.stop()
            RootlessDiagnostics.scanStatus = "Erro BLE:''')

diagnostic_path = main / 'utils/RootlessDiagnostics.kt'
diagnostics = diagnostic_path.read_text(encoding='utf-8')
for old, new in [
    ('    val rejected = AtomicInteger()', '    val rejected = AtomicInteger()\n    val staleBatchResults = AtomicInteger()'),
    ('Etapa: $controlStage', 'Resultados em lote antigos/sem horário válido descartados: $staleBatchResults\nEtapa: $controlStage'),
]:
    if diagnostics.count(old) != 1:
        raise RuntimeError('Missing diagnostics anchor')
    diagnostics = diagnostics.replace(old, new, 1)

templates = Path(__file__).with_name('m51-p9')
policy = (templates / 'M51BatchScanPolicy.kt').read_text(encoding='utf-8')
tests = (templates / 'M51BatchScanPolicyTest.kt').read_text(encoding='utf-8')
# Validate every anchor and template before changing reconstructed sources.
ble_path.write_text(ble, encoding='utf-8')
diagnostic_path.write_text(diagnostics, encoding='utf-8')
(main / 'utils/M51BatchScanPolicy.kt').write_text(policy, encoding='utf-8')
test_dir = base / 'test/java/me/kavishdevar/librepods/utils'
test_dir.mkdir(parents=True, exist_ok=True)
(test_dir / 'M51BatchScanPolicyTest.kt').write_text(tests, encoding='utf-8')
print('p9: M51/API31 batching + cancellable flush; p0-p8 routes and guards preserved')
