#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publish.py — bundle rendered boards into a print kit, and publish kits as
GitHub Releases for the download site.

    python3 publish.py --kit                # bundle every rendered office → out/<folder>/kit/
    python3 publish.py --kit gazipur-sadar  # bundle one
    python3 publish.py                      # upload every kit, rewrite releases.json
    python3 publish.py gazipur-sadar        # upload one
    python3 publish.py gazipur-sadar --no-manifest   # upload only (release.sh does this)
    python3 publish.py --manifest           # rewrite releases.json only
    python3 publish.py --prune              # also delete releases whose config is gone

make.sh runs --kit; release.sh runs make.sh and then the plain form.

A kit, built from out/<folder>/pdf|jpg|png by render.sh:

    <folder>-citizens-charter.pdf         the 8×6 ft board, vector — the file to print
    <folder>-citizens-charter.jpg         the same board as a print image
    <folder>-other-boards-pdf.zip         every other board, PDF
    <folder>-other-boards-print.zip       every other board, print image (JPG;
                                          PNG with alpha for clear media)

Each office is one GitHub Release, tagged board-<folder>; re-publishing
replaces its files in place. The files never enter git — at ~95 MB an
office and 400 offices, they would not fit in a repo or a Pages site
(1 GB). Only releases.json is committed: index.html reads it, and it links
straight to the release downloads. It is rebuilt from GitHub itself, so it
cannot drift from what is actually published.

Needs the gh CLI, logged in with write access to this repo.
"""

import glob
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
from datetime import date

HERE     = os.path.dirname(os.path.abspath(__file__))
OFFICES  = os.path.join(HERE, 'offices')
OUT      = os.path.join(HERE, 'out')
MANIFEST = os.path.join(HERE, 'releases.json')

BOARD    = 'citizens-charter-v2'
BOARD_BN = 'নাগরিক সনদ ও সেবা তথ্য বোর্ড'
SIZE_BN  = '৮ ফুট × ৬ ফুট (৯৬ × ৭২ ইঞ্চি)'
BOARD_IN = 96          # charter width in inches — recovers DPI from pixel width
TAG      = 'board-'    # release tag prefix: board-<folder>

# GitHub refuses release files over 2 GB; stop well short of it
LIMIT = 1900 * 1024 * 1024

# JPEG start-of-frame markers — the ones that carry the image size
SOF = set(range(0xC0, 0xD0)) - set([0xC4, 0xC8, 0xCC])

# kit facts the page shows but GitHub does not store, kept in the release notes
META = re.compile(r'<!-- kit (\{.*?\}) -->')


def kit_names(folder):
    return {
        'charter_pdf': '%s-citizens-charter.pdf' % folder,
        'charter_img': '%s-citizens-charter.jpg' % folder,
        'others_pdf':  '%s-other-boards-pdf.zip' % folder,
        'others_img':  '%s-other-boards-print.zip' % folder,
    }


def human(n):
    if n < 1024 * 1024:
        return '%d KB' % max(1, int(round(n / 1024.0)))
    return '%.1f MB' % (n / (1024.0 * 1024.0))


def jpeg_size(path):
    """Width and height from the JPEG's SOF segment — no Pillow needed."""
    with open(path, 'rb') as f:
        if f.read(2) != b'\xff\xd8':
            return None
        while True:
            b = f.read(1)
            while b and b != b'\xff':
                b = f.read(1)
            while b == b'\xff':
                b = f.read(1)
            if not b:
                return None
            m = ord(b)
            if m == 0x01 or 0xD0 <= m <= 0xD9:     # markers with no length
                continue
            n = struct.unpack('>H', f.read(2))[0]
            if m in SOF:
                h, w = struct.unpack('>HH', f.read(5)[1:5])
                return w, h
            f.seek(n - 2, 1)


def load_configs():
    """(slug, cfg) for every office config, in filename order."""
    out = []
    for name in sorted(os.listdir(OFFICES)):
        if name.endswith('.json'):
            with open(os.path.join(OFFICES, name), encoding='utf-8') as f:
                out.append((os.path.splitext(name)[0], json.load(f)))
    return out


def gh(*args, **kw):
    """Run gh and return its output. On failure raise with gh's error text,
       or with check=False return None."""
    p = subprocess.run(('gh',) + args, cwd=HERE, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    if p.returncode == 0:
        return p.stdout.decode('utf-8', 'replace')
    if kw.get('check', True):
        raise RuntimeError(p.stderr.decode('utf-8', 'replace').strip())
    return None


# ───────────────────────────── kit ────────────────────────────────────
def make_kit(slug, cfg, named):
    """Bundle out/<folder>/pdf|jpg|png into out/<folder>/kit/. An office not
       rendered yet is skipped quietly unless it was asked for by name."""
    folder = cfg['folder']
    src = os.path.join(OUT, folder)
    pdf = os.path.join(src, 'pdf', BOARD + '.pdf')
    jpg = os.path.join(src, 'jpg', BOARD + '.jpg')
    if not os.path.isfile(pdf) or not os.path.isfile(jpg):
        if named:
            print('  ✗ %s  not rendered — run: bash make.sh %s' % (slug, slug))
            return False
        return True

    kit = os.path.join(src, 'kit')
    if os.path.isdir(kit):
        shutil.rmtree(kit)
    os.makedirs(kit)
    names = kit_names(folder)

    shutil.copyfile(pdf, os.path.join(kit, names['charter_pdf']))
    shutil.copyfile(jpg, os.path.join(kit, names['charter_img']))

    others = [p for p in sorted(glob.glob(os.path.join(src, 'pdf', '*.pdf')))
              if os.path.basename(p) != BOARD + '.pdf']
    images = [p for p in sorted(glob.glob(os.path.join(src, 'jpg', '*.jpg')) +
                                glob.glob(os.path.join(src, 'png', '*.png')))
              if os.path.splitext(os.path.basename(p))[0] != BOARD]
    # PDFs shrink when deflated; JPG and PNG are already compressed, so
    # deflating them again costs time and saves nothing — store them
    for key, files, sub, how in (('others_pdf', others, 'pdf',   zipfile.ZIP_DEFLATED),
                                 ('others_img', images, 'print', zipfile.ZIP_STORED)):
        if files:
            with zipfile.ZipFile(os.path.join(kit, names[key]), 'w', how) as z:
                for p in files:
                    z.write(p, '%s-%s/%s' % (folder, sub, os.path.basename(p)))

    print('  ✓ %s  →  out/%s/kit  [%d other boards]' % (slug, folder, len(others)))
    for k in sorted(os.listdir(kit)):
        print('      %-52s %s' % (k, human(os.path.getsize(os.path.join(kit, k)))))
    return True


# ───────────────────────────── upload ─────────────────────────────────
def notes(cfg, kit, names):
    """Release notes: readable text, plus the kit facts releases.json needs."""
    meta = {}
    wh = jpeg_size(os.path.join(kit, names['charter_img']))
    if wh:
        meta['px'] = '%d × %d' % wh
        meta['dpi'] = int(round(wh[0] / float(BOARD_IN)))
    zp = os.path.join(kit, names['others_pdf'])
    if os.path.isfile(zp):
        with zipfile.ZipFile(zp) as z:
            meta['count'] = len(z.namelist())
    return ('%s\n\n%s — %s\n\n'
            '- `%s` — ছাপানোর মূল ফাইল (ভেক্টর PDF)\n'
            '- `%s` — একই বোর্ড, JPG ছবি\n'
            '- `%s` — অন্যান্য বোর্ড, PDF\n'
            '- `%s` — অন্যান্য বোর্ড, ছবি (JPG; স্বচ্ছ মাধ্যমে PNG)\n\n'
            '<!-- kit %s -->\n'
            % (cfg['identity']['office'], BOARD_BN, SIZE_BN,
               names['charter_pdf'], names['charter_img'],
               names['others_pdf'], names['others_img'],
               json.dumps(meta, ensure_ascii=False)))


def upload(slug, cfg, named):
    """Publish out/<folder>/kit/ as release board-<folder>, replacing any
       earlier files of that office."""
    folder = cfg['folder']
    kit = os.path.join(OUT, folder, 'kit')
    names = kit_names(folder)
    files = [os.path.join(kit, n) for n in sorted(names.values())
             if os.path.isfile(os.path.join(kit, n))]
    if not os.path.isfile(os.path.join(kit, names['charter_pdf'])):
        if named:
            print('  ✗ %s  no print kit — run: bash release.sh %s' % (slug, slug))
            return False
        return True
    for p in files:
        if os.path.getsize(p) > LIMIT:
            print('  ✗ %s  %s is %s — over GitHub\'s 2 GB limit. Render at a lower DPI.'
                  % (slug, os.path.basename(p), human(os.path.getsize(p))))
            return False

    tag = TAG + folder
    title = cfg['identity']['office']
    fd, nf = tempfile.mkstemp(suffix='.md')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(notes(cfg, kit, names))
    try:
        seen = gh('release', 'view', tag, '--json', 'assets', check=False)
        if seen is None:
            gh('release', 'create', tag, '--title', title, '--notes-file', nf,
               '--latest=false')
        else:
            gh('release', 'edit', tag, '--title', title, '--notes-file', nf)
            # files from an older kit layout must not linger beside new ones
            for a in json.loads(seen)['assets']:
                if a['name'] not in names.values():
                    gh('release', 'delete-asset', tag, a['name'], '--yes')
        # a dropped connection mid-upload is the usual failure — retry it
        for attempt in (1, 2, 3):
            try:
                gh('release', 'upload', tag, '--clobber', *files)
                break
            except RuntimeError:
                if attempt == 3:
                    raise
                print('      upload interrupted — retrying (%d/3)' % (attempt + 1))
    except RuntimeError as e:
        print('  ✗ %s  upload failed: %s' % (slug, e))
        return False
    finally:
        os.remove(nf)

    total = sum(os.path.getsize(p) for p in files)
    print('  ✓ %s  →  release %s  [%d files, %s]' % (slug, tag, len(files), human(total)))
    return True


def prune(configs, releases):
    keep = set(TAG + cfg['folder'] for _, cfg in configs)
    for tag in sorted(releases):
        if tag not in keep:
            gh('release', 'delete', tag, '--yes', '--cleanup-tag')
            print('  - release %s  deleted (no config names it)' % tag)


# ───────────────────────────── manifest ───────────────────────────────
def fetch_releases():
    """Every board-* release on GitHub → {tag: {'notes': …, 'assets': {name: (bytes, url)}}}."""
    out = gh('api', '--paginate', '--slurp', 'repos/{owner}/{repo}/releases?per_page=100')
    found = {}
    for page in json.loads(out):
        for r in page:
            if r['tag_name'].startswith(TAG) and not r['draft']:
                found[r['tag_name']] = {
                    'notes': r.get('body') or '',
                    'assets': dict((a['name'], (a['size'], a['browser_download_url']))
                                   for a in r['assets']),
                }
    return found


def entry(cfg, rel):
    folder = cfg['folder']
    ident = cfg['identity']
    names = kit_names(folder)

    def info(key):
        a = rel['assets'].get(names[key])
        return {'url': a[1], 'bytes': a[0], 'size': human(a[0])} if a else None

    files = dict((k, info(k)) for k in names)
    if not any(files.values()):
        return None
    m = META.search(rel['notes'])
    meta = json.loads(m.group(1)) if m else {}
    img = files['charter_img']
    if img and 'px' in meta:
        img['px'], img['dpi'] = meta['px'], meta.get('dpi')

    return {
        'folder':    folder,
        'office':    ident['office'],
        'upazila':   ident['upazila'],
        'district':  ident['district'],
        'web':       ident['srWeb'],
        'published': ident['published'],
        'charter':   {'pdf': files['charter_pdf'], 'img': img},
        'others':    {'count': meta.get('count', 0),
                      'pdf': files['others_pdf'], 'img': files['others_img']},
    }


def write_manifest(configs, releases):
    by_district = {}
    for _, cfg in configs:
        rel = releases.get(TAG + cfg['folder'])
        e = entry(cfg, rel) if rel else None
        if e:
            by_district.setdefault(e['district'], []).append(e)
    districts = [{'district': d,
                  'offices': sorted(by_district[d], key=lambda e: e['office'])}
                 for d in sorted(by_district)]
    data = {
        'generated': date.today().isoformat(),
        'board':     BOARD_BN,
        'size':      SIZE_BN,
        'count':     sum(len(d['offices']) for d in districts),
        'districts': districts,
    }

    # keep the old date if nothing else changed — no churn in git for a no-op
    try:
        with open(MANIFEST, encoding='utf-8') as f:
            old = json.load(f)
        if dict(old, generated=None) == dict(data, generated=None):
            data['generated'] = old.get('generated', data['generated'])
    except (IOError, OSError, ValueError):
        pass

    with open(MANIFEST, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print('  releases.json  →  %d office(s) in %d district(s)'
          % (data['count'], len(districts)))


def main():
    # Windows consoles default to cp1252 when piped; never die on a ✓
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='replace')

    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    kit_only = '--kit' in sys.argv
    manifest_only = '--manifest' in sys.argv
    do_prune = '--prune' in sys.argv

    configs = load_configs()
    chosen = configs
    if args:
        chosen = [(s, c) for s, c in configs if s in args or c.get('folder') in args]
        if not chosen:
            sys.exit('No such office config: %s' % ', '.join(args))

    print()
    ok = True
    if kit_only:
        for slug, cfg in chosen:
            ok = make_kit(slug, cfg, bool(args)) and ok
        print()
        sys.exit(0 if ok else 1)

    if not manifest_only:
        for slug, cfg in chosen:
            ok = upload(slug, cfg, bool(args)) and ok
    # release.sh uploads office by office and rebuilds the manifest once
    if '--no-manifest' in sys.argv:
        print()
        sys.exit(0 if ok else 1)
    releases = fetch_releases()
    if do_prune:
        prune(configs, releases)
        releases = fetch_releases()
    write_manifest(configs, releases)
    print()
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
