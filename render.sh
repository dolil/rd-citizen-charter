#!/usr/bin/env bash
# render.sh — one office's HTML → PDF and 300-dpi print image
#
#   bash render.sh out/gazipur-sadar
#   DPI=150 bash render.sh out/gazipur-sadar     # lighter print images
#
# Print images are JPG (quality 95, no chroma subsampling, so small Bengali
# text and white-on-green headings stay crisp). Clear-media files (sticker,
# acrylic plate) are PNG with their alpha channel instead — JPG has no
# transparency, and on clear vinyl the transparency IS the deliverable.
# Do not "simplify" that.
#
# The PDF stays the real deliverable: it is vector and prints sharp at any
# size. 300 dpi is already print quality at 8 × 6 ft, and still ~240 dpi if
# a press scales the board up to 10 ft wide.

set -uo pipefail
DIR="${1:?usage: bash render.sh out/<office-folder>}"
DPI="${DPI:-300}"
CHROME="${CHROME:-/c/Program Files/Google/Chrome/Application/chrome.exe}"

cd "$DIR"; mkdir -p pdf jpg png
# a board dropped from templates/ must not linger in the print kit
# (fb/ is from the old pipeline, which also made Facebook copies)
rm -rf pdf/*.pdf jpg/*.jpg png/*.png fb
WIN="$(pwd -W 2>/dev/null || pwd)"
fail=0

is_clear() { case "$1" in *clear-vinyl*|*acrylic*) return 0 ;; *) return 1 ;; esac; }

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

# The templates pull Tiro Bangla / Hind Siliguri from Google Fonts. If that
# load fails, Chrome silently sets the board in a system Bengali font and
# embeds THAT — a board that looks wrong with no error anywhere. Catch it.
echo; echo "══ 3. fonts"
for f in pdf/*.pdf; do
  printf '   %-56s' "$(basename "$f")"
  fonts="$(pdffonts "$f" | tail -n +3)"
  # columns from the right: ID, object, uni, sub, emb
  unemb="$(echo "$fonts" | awk 'NF && $(NF-4) != "yes" { print $1 }')"
  wrong="$(echo "$fonts" | awk '{ print $1 }' | grep -iE 'Nirmala|Vrinda|Shonar|Lohit|Beng|Kalpurush|Solaiman|Siyam|Mukti' || true)"
  if [ -n "$unemb" ]; then
    echo "FAILED — not embedded: $(echo $unemb)"; fail=1
  elif ! echo "$fonts" | grep -q 'TiroBangla'; then
    echo "FAILED — no Tiro Bangla; the web fonts did not load"; fail=1
  elif [ -n "$wrong" ]; then
    echo "FAILED — system Bengali font used: $(echo $wrong)"; fail=1
  else
    echo ok
  fi
done

echo; echo "══ 4. PDF → print image ($DPI dpi)"
for f in pdf/*.pdf; do
  b="$(basename "${f%.pdf}")"; printf '   %-56s' "$b"
  if is_clear "$b"; then
    pdftocairo -png -r "$DPI" -transp -singlefile "$f" "png/$b"
    magick "png/$b.png" -strip -colorspace sRGB "png/$b.png"
    echo "png (alpha kept)"
  else
    pdftoppm -png -r "$DPI" -singlefile "$f" "jpg/.$b"
    magick "jpg/.$b.png" -background white -alpha remove -alpha off \
           -colorspace sRGB -strip -quality 95 -sampling-factor 4:4:4 "jpg/$b.jpg"
    rm -f "jpg/.$b.png"
    [ -s "jpg/$b.jpg" ] && echo jpg || { echo FAILED; fail=1; }
  fi
done

echo; echo "══ verify — clear media must read srgba, everything else srgb"
magick identify -ping -format "   %f  %wx%h  %[channels]  alpha=%A\n" png/*.png jpg/*.jpg 2>/dev/null
echo
[ "$fail" -eq 0 ] && echo "  All files rendered." || echo "  SOME FILES FAILED — see above."
echo
exit "$fail"
