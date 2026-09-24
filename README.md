# দলিল বোর্ড কিট — Sub-Registry office boards

Every board is shared by all offices except for a handful of values that
genuinely differ. Those live in `offices/<slug>.json`; everything else is
national and lives once, in `templates/`.

## Use

```bash
pip install -r requirements.txt   # once — draws the footer QR
python3 build.py --check          # validate configs, build nothing
python3 build.py                  # build every office  → out/<folder>/
python3 build.py gazipur-sadar    # build one
bash make.sh gazipur-sadar        # build + render + print kit → out/<folder>/kit/
bash release.sh gazipur-sadar     # the same, then publish the kit to the download site
```

**On Windows use `python`, not `python3`.** Windows has no `python3`
command — that name is a Microsoft Store stub that prints an install
message. Either call `python build.py` / `py build.py`, or add
`alias python3=python` to `~/.bashrc`. `make.sh` detects the right one
by itself.

`qrcode` is the only Python dependency, and only for the footer QR of each
office's website — without it the build still succeeds but leaves the
reference office's QR in place, and says so in the build log.

Renderers need Chrome, `poppler-utils` and ImageMagick on PATH.
Set `CHROME=` if Chrome is somewhere unusual.

## What gets printed

`make.sh` renders every board and bundles each office's **print kit**:

```
out/<folder>/kit/
  <folder>-citizens-charter.pdf        the 8×6 ft board, vector — the file to print
  <folder>-citizens-charter.jpg        the same board, 300 dpi (~40 MB)
  <folder>-other-boards-pdf.zip        every other board, PDF
  <folder>-other-boards-print.zip      every other board, 300-dpi print image
```

- **PDF first.** It is vector, so it prints sharp at any size, and every
  font is embedded — the press needs no Bengali font installed.
- **JPG for Photoshop / Illustrator shops.** Illustrator opens a PDF as
  editable text and re-sets the Bengali with its own fonts and engine,
  which breaks conjuncts. An image has no fonts to break. Quality 95 with
  no chroma subsampling (`4:4:4`) keeps small text and white-on-green
  headings clean. 300 dpi is print quality at 8 × 6 ft and still ~240 dpi
  if a press scales the board up to 10 ft wide.
- **PNG only for clear media.** The clear-vinyl sticker and the acrylic
  plate keep their transparency, which JPG cannot hold.

`render.sh` also checks every PDF's fonts and fails the office if a font
is not embedded, or if Tiro Bangla is missing or a system Bengali font
stood in for it. That happens silently when Google Fonts fails to load
during a render, and would otherwise reach the printer.
`DPI=150 bash make.sh …` renders lighter print images.

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
| `folder` | output folder name — `out/<folder>/` and the release tag `board-<folder>`. Usually the same as the JSON's filename. |
| `identity` | office name, upazila, district, bank branch, websites, publication date |
| `grs` | the designated অনিক and appeal officer |
| `section126` | ৫% / ১,৩০০ / ৩,৫০০ in the listed districts, ৩% / ৩০০ / ১,০০০ elsewhere |
| `section125` | set by district SRO — thana names, শ্রেণি bands, per-decimal amounts |
| `sroRef` | the ধারা ১২৫ notification reference printed under the rates |
| `showClasses` | `true`/`false` — show or hide the ভূমির শ্রেণি (ক–চ) table. Offices whose district has no development-authority or developer land need only শ্রেণি চ, so the table is noise there. |
| `showAdvice` | `true`/`false` — show or hide the গুরুত্বপূর্ণ পরামর্শ card. It is there to fill the space the শ্রেণি table leaves when `showClasses` is `false`, so the two are meant to be mutually exclusive: classes on → advice off, and the other way round. |
| `deedRows` | how many of the fee chart's optional deed rows to show, `0`–`8`. The first eight deeds and the নকল row always appear, so the chart never drops below nine rows. |
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

The clear-vinyl sticker and the acrylic plate (the only PNGs) must read
`srgba` with a live alpha — transparency is the deliverable there. The
JPGs should read `srgb`. `render.sh` already handles the distinction; the
check is to catch a pipeline edit that breaks it.

## Download site (GitHub Pages)

Pages serves this repo from `main`, root folder:

| URL | File | Purpose |
|---|---|---|
| `/` | `index.html` | public download directory — every published board, one card per district |

The directory reads `releases.json` and offers each office's print kit —
the charter as PDF and JPG, the other boards as a PDF zip and an image
zip — with a search box across every office, upazila and district.

**The files live in GitHub Releases, not in git.** An office's kit is
~95 MB; ~400 offices is ~38 GB, far past what a repo or a Pages site (1 GB)
can hold. Releases have no total limit and allow 2 GB per file. Each office
is one release, tagged `board-<folder>`; re-publishing replaces its files.
Only `releases.json` is committed, and it links straight to the release
downloads.

To publish offices — one, or a day's batch:

```bash
bash release.sh gazipur-sadar kaliganj …   # per office: make.sh, then upload
git add releases.json && git commit -m "Publish boards" && git push
```

An office that fails (a bad config, the font check, an upload) is
reported and skipped; the rest of the batch carries on, and the summary
prints the command to re-run the failures. Rendering takes ~5½ minutes an
office, most of it the 600-megapixel charter JPG; uploading ~95 MB more.

`publish.py` on its own:

```bash
python3 publish.py --kit gazipur-sadar  # bundle out/<folder>/kit/ (make.sh runs this)
python3 publish.py gazipur-sadar        # upload one kit, rewrite releases.json
python3 publish.py                      # upload every kit in out/
python3 publish.py --manifest           # rewrite releases.json from GitHub only
python3 publish.py --prune              # also delete releases whose config is gone
```

`releases.json` is always rebuilt from what GitHub actually holds, so it
cannot list a file that isn't there. Uploading needs the `gh` CLI logged
in with write access (`gh auth status`).

## The board

`templates/citizens-charter-v2.html` is the board that gets built — the
charter-table version. `templates/reference/` holds the earlier
five-column board; nothing in there is built, it is kept only so the
older wording and fee cards stay findable.

v2 markers: `S125P` and `S126P` (the tax rates as prose, generated from
the same `section125` / `section126` data), `SRO`, `DROFF`, `SRWEB`,
`DRWEB`, `ANIK`, `APPEAL`, `DEEDS`.

## Layout

```
templates/            the board that gets built
templates/reference/  older boards — kept for reference, never built
index.html            Pages: download directory (reads releases.json)
releases.json         the directory's data — written by publish.py, committed
                      (the files themselves: GitHub Releases, tag board-<folder>)
offices/<slug>.json   one file per office
out/<folder>/         generated — never edit, always overwritten
out/<folder>/pdf|jpg|png|kit
build.py              offices + templates → out/
render.sh             one office → PDF, 300-dpi JPG (PNG for clear media)
make.sh               build.py → render.sh → publish.py --kit
release.sh            per office: make.sh → upload; then releases.json
publish.py            print kits, GitHub Releases, releases.json
```
