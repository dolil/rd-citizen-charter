# বোর্ড জেনারেটর — GitHub Pages app

A single page. The user fills a form, sees the board update live beside it,
and downloads a ZIP. No account, no token, no Actions minutes — the
substitution runs in the browser using the same markers and the same rules
as `build.py`.

## Turning it on

Settings → Pages → Source: **Deploy from a branch** → branch `main`,
folder **`/docs`**. The app is then at
`https://<user>.github.io/<repo>/`.

## Keeping the template in step

`docs/templates/` holds a copy of the master board. When a master changes:

```bash
cp templates/*.html docs/templates/
```

The app fetches it at load, so nothing else needs rebuilding. If a new
configurable region is added to a master, add its marker name to the
`build()` function in `docs/index.html` as well as to `build.py` — the two
must handle the same set.

## Why the logic is duplicated

`build.py` runs in CI and on the command line; the app runs in a browser
where Python is not available. Both target the same `<!--@NAME-->` markers
and produce byte-identical output — that equality is worth re-checking
whenever either side changes, by building the same office both ways and
diffing.

## Running it locally

`fetch()` will not read a file off disk, so opening `index.html` directly
shows a template-load error. Serve the folder instead:

```bash
cd docs && python -m http.server
# then open http://localhost:8000
```
