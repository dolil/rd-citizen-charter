# দলিল বোর্ড কিট — Sub-Registry office boards

Every board is shared by all offices except for a handful of values that
genuinely differ. Those live in `offices/<slug>.json`; everything else is
national and lives once, in `templates/`.

## Use

```bash
python3 build.py --check          # validate configs, build nothing
python3 build.py                  # build every office  → out/<folder>/
python3 build.py gazipur-sadar    # build one
bash make.sh gazipur-sadar        # build + render to PDF/PNG/JPG
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
  "compact":    { "s125": "1", "kroy": "1" },
  "showKroy":   true,
  "section125": [ { "label": "ক)", "lead": "…", "items": ["…", "…"] } ],
  "kroy":       [ "…", "…" ]
}
```

### What is configurable, and why

| Key | Why it varies |
|---|---|
| `identity` | office name, upazila, district, bank branch, websites, publication date |
| `grs` | the designated অনিক and appeal officer |
| `section126` | ৫% / ১,৩০০ / ৩,৫০০ in the listed districts, ৩% / ৩০০ / ১,০০০ elsewhere |
| `section125` | set by district SRO — thana names, শ্রেণি bands, per-decimal amounts |
| `showKroy` | `true`/`false` — show or hide the জমি ক্রয়ের পূর্বে সতর্কতা card entirely |
| `kroy` | জমি ক্রয়ের পূর্বে সতর্কতা — trim or extend to fill the column |
| `compact` | `1` = as drawn, `1.3` looser, `0.9` tighter. Most districts have a much shorter ১২৫ text than Gazipur's; raise `s125` to fill the gap that leaves. |

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
magick identify -format "%f %wx%h %[channels] alpha=%A\n" out/<office>/png/*.png
```

The clear-vinyl sticker and the acrylic plate must read `srgba` with a
live alpha — transparency is the deliverable there. Everything else
should read `srgb`. `render.sh` already handles the distinction; the
check is to catch a pipeline edit that breaks it.

## Browser app

`docs/` is a GitHub Pages app: a form with live preview and compactness
sliders, producing the same HTML as `build.py` and downloading it as a
ZIP with its `office.json`. No account or token needed. See
`docs/README.md`.

## Layout

```
templates/            masters — shared, never edited per office
docs/                 GitHub Pages app (index.html + a copy of templates/)
offices/<slug>.json   one file per office
out/<folder>/         generated — never edit, always overwritten
out/<folder>/pdf|png|fb
```
