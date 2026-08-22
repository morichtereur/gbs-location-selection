#!/usr/bin/env bash
# Render the dashboard to PNG in both themes.
#
# The browser preview in the authoring environment returned 59x41 screenshots
# for an entire session, so three rounds of design changes shipped without
# anyone looking at them. Headless Chrome does the job in two seconds and there
# is no excuse for working blind again.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
OUT="$ROOT/data"

if [ ! -x "$CHROME" ]; then
  echo "Chrome not found at $CHROME — set CHROME to a Chromium binary." >&2
  exit 1
fi
if [ ! -f "$ROOT/dashboard.html" ]; then
  echo "dashboard.html missing — run 'make dashboard' first." >&2
  exit 1
fi

# Light needs the attribute stamped; dark is what headless Chrome defaults to.
python3 - "$ROOT/dashboard.html" "$OUT/_light.html" <<'PY'
import pathlib, sys
src = pathlib.Path(sys.argv[1]).read_text()
pathlib.Path(sys.argv[2]).write_text(
    src.replace('<html lang="en">', '<html lang="en" data-theme="light">')
)
PY

"$CHROME" --headless --disable-gpu --hide-scrollbars \
  --window-size=1280,1500 --virtual-time-budget=4000 \
  --screenshot="$OUT/dashboard-light.png" "file://$OUT/_light.html" 2>/dev/null
"$CHROME" --headless --disable-gpu --hide-scrollbars \
  --window-size=1280,1500 --virtual-time-budget=4000 \
  --screenshot="$OUT/dashboard-dark.png" "file://$ROOT/dashboard.html" 2>/dev/null
rm -f "$OUT/_light.html"
echo "wrote data/dashboard-light.png and data/dashboard-dark.png"
