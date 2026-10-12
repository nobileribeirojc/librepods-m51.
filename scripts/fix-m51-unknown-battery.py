#!/usr/bin/env python3
"""M51 follow-up: keep original LibrePods UI but never display unknown battery as 0%.
Applies to the unpacked v4 source during CI. AGPL-3.0-or-later.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1])
base = root / "android/app/src/main/java/me/kavishdevar/librepods/composables"

def edit(name, changes):
    path = base / name
    content = path.read_text(encoding="utf-8")
    for before, after in changes:
        count = content.count(before)
        if count != 1:
            raise SystemExit(f"{name}: expected one match; got {count}: {before[:85]}")
        content = content.replace(before, after, 1)
    path.write_text(content, encoding="utf-8")

edit("BatteryIndicator.kt", [
    ("    val batteryOutlineColor = Color(0xFFBFBFBF)\n",
     "    val hasReading = batteryPercentage in 0..100\n    val batteryOutlineColor = Color(0xFFBFBFBF)\n"),
    ("    val animatedFillWidth by animateFloatAsState(targetValue = batteryPercentage / 100f)",
     "    val animatedFillWidth by animateFloatAsState(targetValue = (if (hasReading) batteryPercentage else 0) / 100f)"),
    ('            text = "$batteryPercentage%",',
     '            text = if (hasReading) "$batteryPercentage%" else "—",'),
])

edit("BatteryView.kt", [
    ("                            left.level,\n                            left.status == BatteryStatus.CHARGING",
     "                            left.level.takeIf { left.status != BatteryStatus.DISCONNECTED } ?: -1,\n                            left.status == BatteryStatus.CHARGING"),
    ("                            right.level,\n                            right.status == BatteryStatus.CHARGING",
     "                            right.level.takeIf { right.status != BatteryStatus.DISCONNECTED } ?: -1,\n                            right.status == BatteryStatus.CHARGING"),
    ("                    BatteryIndicator(case.level, case.status == BatteryStatus.CHARGING)",
     "                    BatteryIndicator(case.level.takeIf { case.status != BatteryStatus.DISCONNECTED } ?: -1, case.status == BatteryStatus.CHARGING)"),
])

print("OK: disconnected/unknown battery now displays — instead of 0%; actual 0% remains valid.")
