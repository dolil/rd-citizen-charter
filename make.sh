#!/usr/bin/env bash
# make.sh — build, render and bundle the print kit in one go
#
#   bash make.sh                   # every office
#   bash make.sh gazipur-sadar     # one office
#   bash make.sh --check           # validate configs only
#   DPI=300 bash make.sh …         # heavier print images (default 150)
#
# Ends with, per office — every board, the charter included, in both:
#   out/<folder>/kit/<folder>-pdf.zip       vector PDFs — the files to print
#   out/<folder>/kit/<folder>-images.zip    150-dpi print images
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
# along with nabinagar). Windows Python ends lines with \r\n; strip the \r,
# or every folder but the last comes back as "name\r" and cannot be found.
FOLDERS=$("$PY" - "$@" <<'EOF' | tr -d '\r'
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
