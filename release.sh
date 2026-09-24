#!/usr/bin/env bash
# release.sh — build, render, bundle and publish to the download site
#
#   bash release.sh                               # every office
#   bash release.sh gazipur-sadar                 # one office
#   bash release.sh gazipur-sadar kaliganj …      # a day's batch
#   DPI=150 bash release.sh nabinagar             # lighter print images (default 300)
#
# Per office: make.sh (build → PDF → print images → font check → kit), then
# publish.py uploads the kit as GitHub Release board-<folder>. An office
# that fails is reported and skipped; the rest of the batch carries on.
# At the end releases.json is rebuilt — commit and push it to update the site.
#
# Needs the gh CLI logged in with write access to this repo (gh auth status).
set -uo pipefail

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

gh auth status >/dev/null 2>&1 || { echo "  gh is not logged in — run: gh auth login"; exit 1; }

if [ $# -eq 0 ]; then
  set -- $(cd offices && ls *.json | sed 's/\.json$//')
fi

failed=()
n=0
for office in "$@"; do
  n=$((n + 1))
  echo; echo "════════ $n/$# — $office"
  if bash make.sh "$office" && "$PY" publish.py "$office" --no-manifest; then
    :
  else
    failed+=("$office")
  fi
done

"$PY" publish.py --manifest

echo "  $(( $# - ${#failed[@]} )) of $# office(s) published."
if [ ${#failed[@]} -gt 0 ]; then
  echo "  FAILED: ${failed[*]}"
  echo "  Fix and re-run:  bash release.sh ${failed[*]}"
fi
echo "  To update the site:  git add releases.json && git commit -m 'Publish boards' && git push"
echo
[ ${#failed[@]} -eq 0 ]
