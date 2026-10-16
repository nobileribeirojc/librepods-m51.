#!/usr/bin/env python3
"""Isolated p9 test variant. This does not migrate p8 data or install an APK."""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: python3 scripts/m51-p9-sidecar.py source/LibrePods-M51-v4")
base = Path(sys.argv[1]) / "android/app"
gradle = base / "build.gradle.kts"
manifest = base / "src/main/AndroidManifest.xml"
strings = base / "src/main/res/values/strings.xml"
service = base / "src/main/java/me/kavishdevar/librepods/services/AirPodsService.kt"

def replace_once(path, old, new):
    src = path.read_text(encoding="utf-8")
    if src.count(old) != 1:
        raise RuntimeError(f"{path}: expected one anchor {old!r}; found {src.count(old)}")
    return src.replace(old, new, 1)

# Keep original namespace/source package; isolate this experimental package id.
gradle_new = replace_once(gradle, '''    buildTypes {
        release {''', '''    buildTypes {
        getByName("debug") {
            applicationIdSuffix = ".p9sidecar"
            versionNameSuffix = "-sidecar"
        }
        release {''')
label_new = replace_once(strings,
    '<string name="app_name" translatable="false">LibrePods M51 (teste)</string>',
    '<string name="app_name" translatable="false">LibrePods M51 p9 (paralelo)</string>')
# Avoid launching a second scanner on device boot.
manifest_new = replace_once(manifest,
    '''android:name=".receivers.BootReceiver"
            android:enabled="true"''',
    '''android:name=".receivers.BootReceiver"
            android:enabled="false"''')
# Use this variant's own URI authority rather than a hardcoded upstream id.
service_new = replace_once(service,
    '.authority("me.kavishdevar.librepods")',
    '.authority(applicationContext.packageName)')
for path, data in ((gradle, gradle_new), (strings, label_new),
                   (manifest, manifest_new), (service, service_new)):
    path.write_text(data, encoding="utf-8")

assert 'applicationId = "me.kavishdevar.librepods.m51test"' in gradle_new
assert 'applicationIdSuffix = ".p9sidecar"' in gradle_new
assert 'android:authorities="${applicationId}.provider"' in manifest_new
print("Experimental sidecar: me.kavishdevar.librepods.m51test.p9sidecar; p8 untouched")
