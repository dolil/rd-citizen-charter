# দলিল বোর্ড কিট — Sub-Registry office boards

Every board is shared by all offices except for a handful of values that
genuinely differ. Those live in `offices/<slug>.json`; everything else is
national and lives once, in `templates/`.

## Use

```bash
python3 build.py --check          # validate configs, build nothing
python3 build.py                  # build every office  → out/<folder>/
python3 build.py gazipur-sadar    # build one
bash make.sh gazipur-sadar        # build + render + print kit → out/<folder>/kit/
```

**On Windows use `python`, not `python3`.** Windows has no `python3`
command — that name is a Microsoft Store stub that prints an install
message. Either call `python build.py` / `py build.py`, or add
`alias python3=python` to `~/.bashrc`. `make.sh` detects the right one
by itself.

Renderers need Chrome, `poppler-utils` and ImageMagick on PATH.
Set `CHROME=` if Chrome is somewhere unusual.

## Adding an office

Copy an existing JSON, change the values, run `--check`, then build.

```json
{
  "folder": "kaliganj",
  "identity": { "office": "…", "upazila": "…", "district": "…",
                "bankBranch": "…", "srWeb": "…",
                "drOffice": "…", "drWeb": "…", "published": "…" },
  "grs":        { "anik": "…", "appeal": "…" },
  "section126": { "plot": "৩%", "residential": "৩০০/-", "commercial": "১,০০০/-" },
  "sroRef":     "এস.আর.ও নং ২১০, তারিখ ০৮ জুন ২০২৬",
  "compact":    { "s125": "1", "board": "1" },
  "deedRows":   8,
  "showClasses": true,
  "showAdvice": false,
  "section125": [ { "label": "ক)", "lead": "…", "items": ["…", "…"] } ]
}
```

### What is configurable, and why

| Key | Why it varies |
|---|---|
| `folder` | output folder name — `out/<folder>/` and the release tag `board-<folder>` |
| `identity` | office name, upazila, district, bank branch, websites, publication date |
| `grs` | the designated অনিক and appeal officer |
| `section126` | ৫% / ১,৩০০ / ৩,৫০০ in the listed districts, ৩% / ৩০০ / ১,০০০ elsewhere |
| `section125` | set by district SRO — thana names, শ্রেণি bands, per-decimal amounts |
| `sroRef` | the ধারা ১২৫ notification reference printed under the rates |
| `showClasses` | `true`/`false` — show or hide the ভূমির শ্রেণি (ক–চ) table |
| `showAdvice` | `true`/`false` — show or hide the গুরুত্বপূর্ণ পরামর্শ card, which fills the space the শ্রেণি table leaves when `showClasses` is `false`. The two are meant to be mutually exclusive. |
| `deedRows` | how many of the fee chart's optional deed rows to show, `0`–`8`. The first eight deeds and the নকল row always appear. |
| `compact` | `s125` scales the উৎসে কর cell of the fee chart; `board` scales every font on the board (`0.7`–`1.3`). `1` = as drawn, above is looser, below tighter. Most districts have a much shorter ১২৫ text than Gazipur's, which leaves a gap — fill it by raising `s125`, or by showing more `deedRows`. |

### What is NOT configurable — on purpose

Stamp দফা rates and ceilings, every registration fee and slab, স্থানীয়
সরকার কর, VAT, দান কর, নকল fees, দলিল লেখকের পারিশ্রমিক, challan codes,
GRS timeframes, the service table, required documents, the steps and all
the notices. These are national. Fixing one in `templates/` corrects it
for every office at once — which is the whole reason for the split. If a
figure here is wrong, it is wrong everywhere, so fix it once and rebuild.

## Validation

`build.py --check` refuses an office rather than printing a defective
board. It catches empty identity or rate fields, a `section125` branch
with no items, more than nine items in a branch (Bengali numerals run
out), and a `compact` value outside 0.5–2.0. CI runs the same check on
every push, so a bad rate fails the PR instead of reaching a printer.

## Before printing

```bash
pdfinfo out/<office>/pdf/<file>.pdf     # page size must match the filename
magick identify -ping -format "%f %wx%h %[channels] alpha=%A\n" out/<office>/png/*.png out/<office>/jpg/*.jpg
```

Print images are 300-dpi JPGs, except the clear-vinyl sticker and the
acrylic plate, which are PNGs and must read `srgba` with a live alpha —
transparency is the deliverable there. The JPGs should read `srgb`. `render.sh` already handles the distinction; the
check is to catch a pipeline edit that breaks it.

## Download site

Pages serves the repo root: `/` is the public download directory
(`index.html`, reading `releases.json`). Publish offices with `bash release.sh <office> …`, which uploads
each print kit as a GitHub Release, then commit `releases.json`. The full
workflow is in the root `README.md`.

## The board

`templates/citizens-charter-v2.html` is the board that gets built.
`templates/reference/citizens-charter-v1.html` is the earlier five-column
board, kept for reference and never built.

v2 markers: `S125P` and `S126P` (the tax rates as prose, generated from
the same `section125` / `section126` data), `SRO`, `DROFF`, `SRWEB`,
`DRWEB`, `ANIK`, `APPEAL`, `DEEDS`.

## Layout

```
templates/            masters — shared, never edited per office
index.html            Pages: download directory
releases.json         download site data (files: GitHub Releases)
offices/<slug>.json   one file per office
out/<folder>/         generated — never edit, always overwritten
out/<folder>/pdf|jpg|png|kit
```
