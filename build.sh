#!/bin/sh
# Rebuild dist/*.AppImage from AppDir/. Downloads appimagetool and the
# type2 runtimes into .cache/ on first run.
set -eu
cd "$(dirname "$0")"
CACHE=.cache
REL=https://github.com/AppImage
mkdir -p "$CACHE" dist
find AppDir -name __pycache__ -prune -exec rm -rf {} +

fetch() { [ -s "$CACHE/$2" ] || curl -fsSL -o "$CACHE/$2" "$1/$2"; }
fetch "$REL/appimagetool/releases/download/continuous" appimagetool-x86_64.AppImage
chmod +x "$CACHE/appimagetool-x86_64.AppImage"

for arch in x86_64 aarch64; do
    fetch "$REL/type2-runtime/releases/download/continuous" "runtime-$arch"
    ARCH=$arch APPIMAGE_EXTRACT_AND_RUN=1 "$CACHE/appimagetool-x86_64.AppImage" \
        --no-appstream --runtime-file "$CACHE/runtime-$arch" \
        AppDir "dist/Desktop_ID_Probe-$arch.AppImage"
done
