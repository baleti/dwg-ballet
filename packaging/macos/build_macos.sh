#!/bin/sh
# Build dwg-ballet.app (+ dmg when hdiutil exists) on macOS. Untested on hardware (no Mac available); CI builds it.
# Not notarized: needs an Apple developer account. Users open it once via right click > Open (Gatekeeper).
# Limitation: a shell launcher does not receive Finder double-click documents (Apple Events); use "open -a dwg-ballet --args FILE" or drag onto the app until a small native launcher is added.
# usage: packaging/macos/build_macos.sh [OUT_DIR]
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$HERE/../.."; OUT="${1:-$ROOT/dist}"
APP="$OUT/dwg-ballet.app"; rm -rf "$APP"; mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
python3 "$HERE/../stage.py" "$OUT"
cp -R "$OUT/app" "$APP/Contents/Resources/app"
python3 -m venv "$APP/Contents/Resources/venv"
"$APP/Contents/Resources/venv/bin/pip" install -q -r "$OUT/requirements.txt"
cp "$HERE/Info.plist" "$APP/Contents/Info.plist"
cat > "$APP/Contents/MacOS/dwg-ballet" <<'L'
#!/bin/sh
R="$(cd "$(dirname "$0")/../Resources" && pwd)"
cd "$R/app" && exec "$R/venv/bin/python" -m dwgballet "$@"
L
chmod +x "$APP/Contents/MacOS/dwg-ballet"
if command -v hdiutil >/dev/null; then hdiutil create -quiet -volname dwg-ballet -srcfolder "$APP" -ov -format UDZO "$OUT/dwg-ballet.dmg"; fi
echo "built $APP"
