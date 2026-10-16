#!/usr/bin/env python3
"""Static integration checks on the ACTUAL reconstructed Android source.

These checks are not Android runtime tests or a substitute for JUnit/device QA.
"""
from pathlib import Path
import sys
import unittest

root = Path(sys.argv.pop(1)) / 'android/app/src/main/java/me/kavishdevar/librepods'

class ReconstructedSourceChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ble = (root / 'utils/BLEManager.kt').read_text(encoding='utf-8')
        cls.service = (root / 'services/AirPodsService.kt').read_text(encoding='utf-8')

    def test_old_callback_is_stopped_before_new_callback_assignment(self):
        start = self.ble.index('fun startScanning(')
        stop = self.ble.index('mBluetoothLeScanner?.stopScan(previousCallback)', start)
        assign = self.ble.index('mScanCallback = object : ScanCallback()', start)
        self.assertLess(stop, assign)

    def test_late_single_and_batch_callbacks_cannot_deliver_data(self):
        for entry, delivery in [('override fun onScanResult(', 'processScanResult(result)'),
                                ('override fun onBatchScanResults(', 'processedAddresses.clear()')]:
            offset = self.ble.index(entry)
            guard = self.ble.index('if (mScanCallback !== this) return', offset)
            self.assertLess(guard, self.ble.index(delivery, offset))

    def test_internal_retries_do_not_reset_failure_budget(self):
        self.assertIn('if (!automaticRetry) m51ScanPolicy.reset()', self.ble)
        self.assertEqual(3, self.ble.count('automaticRetry = true'))
        failed = self.ble.index('val next = m51ScanPolicy.failed(errorCode)')
        terminal = self.ble.index('if (next == null)', failed)
        schedule = self.ble.index('m51RetryTask = Runnable', failed)
        self.assertLess(terminal, schedule)

    def test_unknown_lid_survives_decoder_to_popup_policy(self):
        decoder = (root / 'utils/PublicProximity.kt').read_text(encoding='utf-8')
        policy = (root / 'utils/CasePopupPolicy.kt').read_text(encoding='utf-8')
        self.assertIn('val lidKnown: Boolean', decoder)
        self.assertIn('lidKnown = reading.lidKnown', self.ble)
        self.assertIn('lidKnown = device.lidKnown', self.service)
        self.assertLess(policy.index('if (!lidKnown) return false'), policy.index('seen[address] ='))

    def test_prior_battery_and_transport_paths_remain(self):
        self.assertIn('receiveManuallySelectedBleBattery(device)', self.service)
        self.assertIn('receiveAutomaticNearbyBattery(device, rssiDbm)', self.service)
        self.assertIn('if (manualBleAddress != null || (isConnectedLocally && aacpReady)) return@post', self.service)
        self.assertIn('M51ControlTransportPolicy.mayAttempt(', self.service)
        self.assertIn('M51ControlTransportPolicy.allowAutomaticL2cap(Build.VERSION.SDK_INT)', self.service)

if __name__ == '__main__':
    unittest.main(verbosity=2)
