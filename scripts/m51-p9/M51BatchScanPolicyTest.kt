package me.kavishdevar.librepods.utils

import org.junit.Assert.*
import org.junit.Test

class M51BatchScanPolicyTest {
    private class Scheduler {
        val queue = mutableListOf<Runnable>()
        val delays = mutableListOf<Long>()
        fun schedule(task: Runnable, delay: Long) { queue.add(task); delays.add(delay) }
        fun cancel(task: Runnable) { queue.removeAll { it === task } }
        fun tick() { queue.removeAt(0).run() }
    }

    @Test fun compatibilityIsRestrictedToM51Android12() {
        assertTrue(M51BatchScanPolicy.enabled(31, "samsung", "SM-M515F"))
        assertTrue(M51BatchScanPolicy.enabled(31, "SAMSUNG", "sm-m515f"))
        assertFalse(M51BatchScanPolicy.enabled(30, "samsung", "SM-M515F"))
        assertFalse(M51BatchScanPolicy.enabled(32, "samsung", "SM-M515F"))
        assertFalse(M51BatchScanPolicy.enabled(31, "samsung", "SM-A515F"))
        assertFalse(M51BatchScanPolicy.enabled(31, "other", "SM-M515F"))
    }

    @Test fun controllerTimestampsMustBeRecentAndPlausible() {
        val now = 60_000_000_000L
        assertTrue(M51BatchScanPolicy.isFresh(now, now))
        assertTrue(M51BatchScanPolicy.isFresh(now - 15_000_000_000L, now))
        assertFalse(M51BatchScanPolicy.isFresh(now - 15_000_000_001L, now))
        assertFalse(M51BatchScanPolicy.isFresh(now + 1, now))
        assertFalse(M51BatchScanPolicy.isFresh(0, now))
        assertFalse(M51BatchScanPolicy.isFresh(-1, now))
    }

    @Test fun flushRepeatsWithoutRestartingTheScannerAndStopsCleanly() {
        val scheduler = Scheduler()
        var flushes = 0
        val pump = M51BatchScanPump(scheduler::schedule, scheduler::cancel) { fail("Unexpected failure") }
        pump.start({ true }) { flushes++ }
        assertEquals(0, flushes)
        repeat(3) { scheduler.tick() }
        assertEquals(3, flushes)
        assertEquals(1, scheduler.queue.size)
        assertTrue(scheduler.delays.all { it == 2_000L })
        pump.stop()
        assertTrue(scheduler.queue.isEmpty())
    }

    @Test fun oldScheduledTasksCannotFlushAReplacementSession() {
        val scheduler = Scheduler()
        var oldFlushes = 0
        var newFlushes = 0
        val pump = M51BatchScanPump(scheduler::schedule, scheduler::cancel) { fail("Unexpected failure") }
        pump.start({ true }) { oldFlushes++ }
        val stale = scheduler.queue.single()
        pump.start({ true }) { newFlushes++ }
        stale.run()
        assertEquals(0, oldFlushes)
        assertEquals(1, scheduler.queue.size)
        scheduler.tick()
        assertEquals(1, newFlushes)
    }

    @Test fun obsoleteCallbackStopsWithoutFlushingOrRescheduling() {
        val scheduler = Scheduler()
        var current = true
        var flushes = 0
        val pump = M51BatchScanPump(scheduler::schedule, scheduler::cancel) { fail("Unexpected failure") }
        pump.start({ current }) { flushes++ }
        current = false
        scheduler.tick()
        assertEquals(0, flushes)
        assertTrue(scheduler.queue.isEmpty())
    }

    @Test fun permissionFailureIsReportedOnceWithoutAFlushRetryLoop() {
        val scheduler = Scheduler()
        var failures = 0
        var calls = 0
        val pump = M51BatchScanPump(scheduler::schedule, scheduler::cancel) { failures++ }
        pump.start({ true }) { calls++; throw SecurityException("revoked") }
        scheduler.tick()
        assertEquals(1, failures)
        assertEquals(1, calls)
        assertTrue(scheduler.queue.isEmpty())
    }

    @Test fun stopDuringFlushCannotRearmTheTask() {
        val scheduler = Scheduler()
        val pump = M51BatchScanPump(scheduler::schedule, scheduler::cancel) { fail("Unexpected failure") }
        pump.start({ true }) { pump.stop() }
        scheduler.tick()
        assertTrue(scheduler.queue.isEmpty())
    }

    @Test fun observedM51PublicHeadersDecodeLikeTheCapodReference() {
        // HCI 2026-10-16, public prefix only. The unused encrypted tail is
        // deliberately omitted and padded, never asserted as decrypted data.
        val headers = listOf("07190127203487b5110000", "07190127203587b5110004",
            "07190127205578b5110004", "07190127203587b5110000", "07190127205578b5110000")
        for (header in headers) {
            val publicBytes = header.chunked(2).map { it.toInt(16).toByte() }.toByteArray().copyOf(27)
            val frame = requireNotNull(PublicProximity.frame(publicBytes))
            val reading = requireNotNull(PublicProximity.decode(frame))
            assertEquals(0x2720, reading.modelId)
            assertEquals(70, reading.left)
            assertEquals(80, reading.right)
            assertEquals(50, reading.case)
            assertTrue(reading.leftCharging && reading.rightCharging)
            assertTrue(reading.lidKnown && reading.lidOpen)
        }
    }
}
