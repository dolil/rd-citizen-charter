#!/usr/bin/env bash
# render.sh — one office's HTML → PDF, 300-dpi PNG, Facebook JPG
#
#   bash render.sh out/gazipur-sadar
#
# Clear-media files (sticker, acrylic plate) keep their alpha channel;
# everything else is flattened to white. Do not "simplify" that — on
# clear vinyl the transparency IS the deliverable.

set -uo pipefail
DIR="${1:?usage: bash render.sh out/<office-folder>}"
CHROME="${CHROME:-/c/Program Files/Google/Chrome/Application/chrome.exe}"

cd "$DIR"; mkdir -p pdf png fb
WIN="$(pwd -W 2>/dev/null || pwd)"
fail=0

echo; echo "══ 1. HTML → PDF"
for f in *.html; do
  [ -e "$f" ] || continue
  b="${f%.html}"; printf '   %-56s' "$b"
  "$CHROME" --headless=new --disable-gpu --no-pdf-header-footer \
    --virtual-time-budget=20000 \
    --print-to-pdf="${WIN}\\pdf\\${b}.pdf" "${WIN}\\${f}" >/dev/null 2>&1
  [ -s "pdf/${b}.pdf" ] && echo ok || { echo FAILED; fail=1; }
done

echo; echo "══ 2. page sizes"
for f in pdf/*.pdf; do
  printf '   %-56s %s\n' "$(basename "$f")" "$(pdfinfo "$f" | sed -n 's/^Page size: *//p')"
done

echo; echo "══ 3–4. PDF → PNG"
for f in pdf/*.pdf; do
  b="$(basename "${f%.pdf}")"; printf '   %-56s' "$b"
  case "$b" in
    *clear-vinyl*|*acrylic*)
      pdftocairo -png -r 300 -transp -singlefile "$f" "png/$b"
      magick "png/$b.png" -strip -colorspace sRGB "png/$b.png"; echo "ok (alpha kept)" ;;
    *)
      pdftoppm -png -r 300 -singlefile "$f" "png/$b"
      magick "png/$b.png" -background white -alpha remove -alpha off \
             -colorspace sRGB -strip "png/$b.png"; echo ok ;;
  esac
done

echo; echo "══ 5. Facebook copies (long edge 2048)"
magick mogrify -path fb -format jpg -background white -alpha remove -alpha off \
  -resize "2048x2048>" -colorspace sRGB -quality 88 -strip png/*.png
echo "   done"

echo; echo "══ verify — clear media must read srgba"
magick identify -format "   %f  %wx%h  %[channels]  alpha=%A\n" png/*.png
echo
[ "$fail" -eq 0 ] && echo "  All files rendered." || echo "  SOME FILES FAILED — see step 1."
echo
