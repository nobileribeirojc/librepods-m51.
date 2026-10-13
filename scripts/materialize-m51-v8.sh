#!/usr/bin/env bash
# Reconstruct the *existing* LibrePods M51 v8 Android source without modifying the v4 ZIP.
# Same order as .github/workflows/build-m51-v4-from-zip.yml.
# This is preparation for local development / Work / Codex, not a new application.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DEST="source/LibrePods-M51-v4"
ZIP="LibrePods-M51-v4-pronto-para-compilar.zip"

if [[ -e "$DEST" ]]; then
  printf 'ERROR: %s already exists. Refusing to overwrite local work.\n' "$DEST" >&2
  exit 2
fi
if [[ ! -s "$ZIP" ]]; then
  printf 'ERROR: missing original v4 ZIP: %s\n' "$ZIP" >&2
  exit 2
fi
for command in python3 unzip git; do
  if ! command -v "$command" >/dev/null 2>&1; then
    printf 'ERROR: required executable not found: %s\n' "$command" >&2
    exit 2
  fi
done

mkdir -p source
# Roll back only a fresh extraction on error; NEVER remove a preexisting source.
trap 'if [[ -d "$DEST" ]]; then rm -rf -- "$DEST"; fi' ERR
unzip -q "$ZIP" -d source
test -f "$DEST/android/settings.gradle.kts"
test -f "$DEST/tools/verify-m51-source.py"

python3 "$DEST/tools/verify-m51-source.py"
python3 scripts/fix-m51-unknown-battery.py "$DEST"
python3 scripts/m51-v5-public-ble-preview.py "$DEST"
python3 scripts/m51-v6-ble-continuo.py "$DEST"
git apply --directory="$DEST" scripts/m51-v7.patch
python3 scripts/m51-v8-lifecycle-ble.py "$DEST"
grep -q 'versionName = "0.1.0-rc.4-m51-v8"' "$DEST/android/app/build.gradle.kts"

trap - ERR
printf '\nPASS: reconstructed LibrePods M51 v8 at %s\n' "$ROOT/$DEST"
printf 'Next: cd source/LibrePods-M51-v4/android && chmod +x gradlew && ./gradlew :app:testDebugUnitTest :app:assembleDebug --no-daemon --stacktrace\n'
