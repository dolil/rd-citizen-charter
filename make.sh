#!/usr/bin/env bash
# make.sh — build, render and bundle the print kit in one go
#
#   bash make.sh                   # every office
#   bash make.sh gazipur-sadar     # one office
#   bash make.sh --check           # validate configs only
#   DPI=150 bash make.sh …         # lighter print images (default 300)
#
# Ends with, per office:
#   out/<folder>/kit/<folder>-citizens-charter.pdf     the 8×6 ft board, vector
#   out/<folder>/kit/<folder>-citizens-charter.jpg     the same, print image
#   out/<folder>/kit/<folder>-other-boards-pdf.zip     every other board, PDF
#   out/<folder>/kit/<folder>-other-boards-print.zip   every other board, print image
set -euo pipefail

# Windows installs Python as "python" / "py"; "python3" is a Microsoft
# Store stub that prints an install message instead of running anything.
if   command -v python3 >/dev/null 2>&1 && python3 -c '' 2>/dev/null; then PY=python3
elif command -v python  >/dev/null 2>&1 && python  -c '' 2>/dev/null; then PY=python
elif command -v py      >/dev/null 2>&1; then PY=py
else
  echo "  No working Python found. On Windows try:  python build.py"
  echo "  If 'python' opens the Microsoft Store, turn off the alias:"
  echo "  Settings > Apps > Advanced app settings > App execution aliases"
  exit 1
fi

case " $* " in *" --check "*) exec "$PY" build.py --check ;; esac

"$PY" build.py "$@"

# a config's slug and its output folder can differ — ask the configs, and
# match names exactly (a substring match would take brahmanbaria-nabinagar
# along with nabinagar)
FOLDERS=$("$PY" - "$@" <<'EOF'
import json, os, sys
want = [a for a in sys.argv[1:] if not a.startswith('-')]
for name in sorted(os.listdir('offices')):
    if not name.endswith('.json'):
        continue
    cfg = json.load(open(os.path.join('offices', name), encoding='utf-8'))
    if not want or name[:-5] in want or cfg['folder'] in want:
        print(cfg['folder'])
EOF
)

for folder in $FOLDERS; do
  echo; echo "──────── rendering out/$folder"
  bash render.sh "out/$folder"
done

"$PY" publish.py --kit "$@"
