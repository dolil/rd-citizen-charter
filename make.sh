#!/usr/bin/env bash
# make.sh — build and render in one go
#
#   bash make.sh                 # every office
#   bash make.sh gazipur-sadar   # one office
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

"$PY" build.py "$@"
for d in out/*/; do
  [ -d "$d" ] || continue
  case "${1:-}" in "" ) ;; *) [[ "$d" == *"$1"* ]] || continue ;; esac
  echo; echo "──────── rendering $d"
  bash render.sh "$d"
done
