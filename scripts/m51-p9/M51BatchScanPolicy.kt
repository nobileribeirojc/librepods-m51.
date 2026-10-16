/* LibrePods M51 extension, AGPL-3.0-or-later. */
package me.kavishdevar.librepods.utils

internal object M51BatchScanPolicy {
    const val REPORT_DELAY_MS = 5_000L
    const val FLUSH_INTERVAL_MS = 2_000L
    private const val MAX_AGE_NS = 15_000_000_000L

    fun enabled(sdk: Int, manufacturer: String, model: String): Boolean =
        sdk == 31 && manufacturer.equals("samsung", ignoreCase = true) &&
            model.startsWith("SM-M515", ignoreCase = true)

    // Do not present an old controller batch as a new lid/ear/battery event.
    fun isFresh(timestampNanos: Long, nowNanos: Long): Boolean =
        timestampNanos > 0 && nowNanos >= timestampNanos &&
            nowNanos - timestampNanos <= MAX_AGE_NS
}

/** One scheduled flush, bound to one scanner/callback generation. */
internal class M51BatchScanPump(
    private val schedule: (Runnable, Long) -> Unit,
    private val cancel: (Runnable) -> Unit,
    private val onFailure: (RuntimeException) -> Unit
) {
    private var task: Runnable? = null

    @Synchronized fun stop() {
        val previous = task
        task = null
        previous?.let(cancel)
    }

    @Synchronized fun start(isCurrent: () -> Boolean, flush: () -> Unit) {
        stop()
        val next = object : Runnable {
            override fun run() = synchronized(this@M51BatchScanPump) {
                if (task !== this || !isCurrent()) {
                    if (task === this) task = null
                    return@synchronized
                }
                try {
                    flush()
                } catch (error: RuntimeException) {
                    task = null
                    onFailure(error)
                    return@synchronized
                }
                if (task === this && isCurrent()) {
                    schedule(this, M51BatchScanPolicy.FLUSH_INTERVAL_MS)
                }
            }
        }
        task = next
        schedule(next, M51BatchScanPolicy.FLUSH_INTERVAL_MS)
    }
}
