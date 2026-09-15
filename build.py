#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build.py — render one office's board set, or every office, from JSON.

    python3 build.py                        # all offices in offices/
    python3 build.py gazipur-sadar          # just one
    python3 build.py --check                # validate configs, build nothing

Templates live in templates/ and are never edited per office. Anything
that differs between offices lives in offices/<slug>.json. Configurable
regions in the HTML are marked:

    <!--@NAME--> … <!--/@NAME-->      block, on its own lines
    <!--@NAME-->…<!--/@NAME-->        inline, within one line

Adding a configurable region later means adding a marker and a key —
no change to this script's structure.
"""

import json
import os
import re
import shutil
import sys

HERE      = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(HERE, 'templates')
OFFICES   = os.path.join(HERE, 'offices')
OUT       = os.path.join(HERE, 'out')

BN = '০১২৩৪৫৬৭৮৯'

# strings in the master that carry the reference office's identity
MASTER = {
    'office':     'সদর সাব-রেজিস্ট্রারের কার্যালয়, সদর, গাজীপুর',
    'office_alt': 'সাব-রেজিস্ট্রারের কার্যালয়, সিরাজদিখান, মুন্সীগঞ্জ',
    'bankBranch': 'সোনালী ব্যাংক, সদর, গাজীপুর শাখা',
    'bankLine':   'ফিসাদি সোনালী ব্যাংক, সিরাজদিখান শাখায় জমা করতে হবে।',
    'srWeb':      'www.sr.sadar.gazipur.gov.bd',
    'drWeb':      'www.dr.gazipur.gov.bd',
    'drOffice':   'জেলা রেজিস্ট্রার, গাজীপুর',
    'published':  'প্রকাশকাল: জুলাই, ২০২৬',
    'upazila':    'সিরাজদিখান',
    'district':   'মুন্সীগঞ্জ',
}

REQUIRED = {
    'folder': str,
    'identity': ['office', 'upazila', 'district', 'bankBranch',
                 'srWeb', 'drOffice', 'drWeb', 'published'],
    'grs': ['anik', 'appeal'],
    'section126': ['plot', 'residential', 'commercial'],
    'compact': ['s125', 'board'],
}


# ───────────────────────────── validation ─────────────────────────────
def validate(cfg, name):
    """Return a list of problems. An office that fails does not get built —
       a board with a missing rate is worse than no board."""
    bad = []
    if not isinstance(cfg.get('folder'), str) or not cfg['folder']:
        bad.append('folder: missing')
    for section, keys in REQUIRED.items():
        if section == 'folder':
            continue
        block = cfg.get(section)
        if not isinstance(block, dict):
            bad.append('%s: missing section' % section); continue
        for k in keys:
            if not str(block.get(k, '')).strip():
                bad.append('%s.%s: empty' % (section, k))

    rows = cfg.get('section125')
    if not isinstance(rows, list) or not rows:
        bad.append('section125: needs at least one branch')
    else:
        for i, r in enumerate(rows, 1):
            for k in ('label', 'lead'):
                if not str(r.get(k, '')).strip():
                    bad.append('section125[%d].%s: empty' % (i, k))
            if not isinstance(r.get('items'), list) or not r['items']:
                bad.append('section125[%d].items: needs at least one line' % i)
            elif len(r['items']) > 9:
                bad.append('section125[%d].items: more than 9 (Bengali numerals run out)' % i)

    if not str(cfg.get('sroRef', '')).strip():
        bad.append('sroRef: empty (the ধারা ১২৫ notification reference)')

    n = cfg.get('deedRows')
    if n is not None:
        try:
            n = int(n)
            if not 0 <= n <= 8:
                bad.append('deedRows: %s is outside 0–8 (optional deed rows to keep)' % n)
        except (TypeError, ValueError):
            bad.append('deedRows: not a number')

    for k in ('s125', 'board'):
        try:
            v = float(cfg.get('compact', {}).get(k, 1))
            if not 0.7 <= v <= 1.3 if k == 'board' else not 0.5 <= v <= 2.0:
                bad.append('compact.%s: %s is outside 0.5–2.0' % (k, v))
        except (TypeError, ValueError):
            bad.append('compact.%s: not a number' % k)
    return bad


# ───────────────────────────── generators ─────────────────────────────
def gen_s125(cfg):
    out = ['<table class="inner">']
    for row in cfg['section125']:
        out.append('                <tr>')
        out.append('                  <td class="k">%s</td>' % row['label'])
        out.append('                  <td>%s' % row['lead'])
        out.append('                    <table class="inner2">')
        for n, item in enumerate(row['items'], 1):
            out.append('                      <tr><td class="k2">%s।</td><td>%s</td></tr>'
                       % (BN[n], item))
        out.append('                    </table>')
        out.append('                  </td>')
        out.append('                </tr>')
    out.append('              </table>')
    return '\n'.join(out)


def trim_deeds(html, keep):
    """The fee chart's rows 9+ sit inside <!--@DEEDS-->. Offices whose ধারা ১২৫
       text is short have spare height and can show more of them; those with a
       long ১২৫ block keep fewer. keep = how many of the optional rows to show."""
    m = re.search(r'(<!--@DEEDS-->\n)([\s\S]*?)(\s*<!--/@DEEDS-->)', html)
    if not m:
        return html, None
    rows = re.findall(r'            <tr><td class="c">[\s\S]*?</tr>\n', m.group(2))
    kept = rows[:keep]
    html = html[:m.start(2)] + ''.join(kept) + html[m.end(2):]

    # renumber the whole chart so the ক্রমিক column stays continuous
    i = html.index('<table class="charter feechart">')
    head, tail = html[:i], html[i:]
    BN = '০১২৩৪৫৬৭৮৯'
    def bn(n):
        return ''.join(BN[int(d)] for d in str(n))
    for k, old in enumerate(re.findall(r'<tr><td class="c">([০-৯]+)</td>', tail), 1):
        tail = tail.replace('<tr><td class="c">%s</td>' % old,
                            '<tr><td class="c">\x00%d\x00</td>' % k, 1)
    for k in range(1, 40):
        tail = tail.replace('\x00%d\x00' % k, bn(k))
    return head + tail, (len(rows), len(kept))


def drop_card(html, name):
    """Remove a whole marked card. Used when an office switches a
       section off — the markers stay in the master, so turning it back
       on later is a one-word change in the JSON."""
    pat = re.compile(r'[ \t]*<!--@%s-->.*?<!--/@%s-->\n?' % (name, name), re.S)
    return pat.sub('', html, count=1)


def gen_s125_prose(cfg):
    """v2 states ধারা ১২৫ as prose inside a fee cell rather than as a table.
       A branch with one item reads as a sentence; a branch with several
       gets them numbered, since those are separate cases with their own
       rates — a district may charge ৩% inside the পৌরসভা and ২% outside."""
    BN = '০১২৩৪৫৬৭৮৯'
    out = ['<b>উৎসে কর [ধারা ১২৫]</b> — ']
    for row in cfg['section125']:
        lead = row['lead'].strip().rstrip(':').rstrip('—').strip()
        items = row['items']
        if len(items) == 1:
            out.append('%s — %s<br>' % (lead, items[0]))
        else:
            out.append('%s:<br>' % lead)
            for k, it in enumerate(items, 1):
                out.append('%s) %s<br>' % (BN[k], it))
    return ''.join(out)


def gen_s126_prose(cfg):
    s = cfg['section126']
    return ('<b>উৎসে কর [ধারা ১২৬]</b> — বাণিজ্যিক ভিত্তিতে প্লট বা ফ্ল্যাট বিক্রয়ের ক্ষেত্রে অতিরিক্ত — '
            'প্লট/জমিতে %s; বিল্ডিং/ফ্ল্যাটে প্রতি বর্গমিটারে আবাসিক %s ও বাণিজ্যিক %s।<br>'
            % (s['plot'], s['residential'], s['commercial']))


def gen_126(cfg):
    s = cfg['section126']
    return '<br>%s<br><br>%s<br>%s' % (s['plot'], s['residential'], s['commercial'])


# ───────────────────────────── substitution ───────────────────────────
def put_block(html, name, repl):
    pat = re.compile(r'(<!--@%s-->).*?(<!--/@%s-->)' % (name, name), re.S)
    if not pat.search(html):
        return html, False
    return pat.sub(lambda m: '%s\n%s\n              %s' % (m.group(1), repl, m.group(2)),
                   html, count=1), True


def put_inline(html, name, repl):
    pat = re.compile(r'(<!--@%s-->).*?(<!--/@%s-->)' % (name, name), re.S)
    if not pat.search(html):
        return html, False
    return pat.sub(lambda m: m.group(1) + repl + m.group(2), html, count=1), True


def swap_identity(html, cfg):
    i = cfg['identity']
    pairs = [
        (MASTER['office'],     i['office']),
        (MASTER['office_alt'], i['office']),
        (MASTER['bankBranch'], i['bankBranch']),
        (MASTER['bankLine'],   'ফিসাদি %s-এ জমা করতে হবে।' % i['bankBranch']),
        (MASTER['srWeb'],      i['srWeb']),
        (MASTER['drWeb'],      i['drWeb']),
        (MASTER['drOffice'],   i['drOffice']),
        (MASTER['published'],  i['published']),
        (MASTER['upazila'],    i['upazila']),     # bare names last
        (MASTER['district'],   i['district']),
    ]
    n = 0
    for old, new in pairs:
        if old and new and old != new and old in html:
            n += html.count(old)
            html = html.replace(old, new)
    return html, n


# ───────────────────────────── build ──────────────────────────────────
def build_office(path, check_only=False):
    slug = os.path.splitext(os.path.basename(path))[0]
    cfg = json.load(open(path, encoding='utf-8'))

    problems = validate(cfg, slug)
    if problems:
        print('  ✗ %s' % slug)
        for p in problems:
            print('      %s' % p)
        return False
    if check_only:
        print('  ✓ %s' % slug)
        return True

    dest = os.path.join(OUT, cfg['folder'])
    os.makedirs(dest, exist_ok=True)
    s125, s126 = gen_s125(cfg), gen_126(cfg)
    show_kroy = cfg.get('showKroy', True)
    built = []

    for name in sorted(os.listdir(TEMPLATES)):
        if name == 'reference':
            continue
        src = os.path.join(TEMPLATES, name)
        # templates/reference/ is kept for reference only and never built
        if not os.path.isfile(src) or name.startswith('.') or name.endswith('.txt'):
            continue
        out_name = name.replace('sirajdikhan', cfg['folder']).replace('gazipur-sadar', cfg['folder'])

        if not name.lower().endswith('.html'):
            shutil.copy2(src, os.path.join(dest, out_name))
            continue

        html = open(src, encoding='utf-8').read()
        html, hits = swap_identity(html, cfg)
        if not cfg.get('showClasses', True):
            html = drop_card(html, 'CLASSCARD')

        marks = []
        for fn, key, val in ((put_block,  'S125',   s125),
                             (put_inline, 'S126',   s126),
                             (put_inline, 'S125P',  gen_s125_prose(cfg)),
                             (put_inline, 'S126P',  gen_s126_prose(cfg)),
                             (put_inline, 'SRO',    cfg.get('sroRef', '')),
                             (put_inline, 'DROFF',  cfg['identity']['drOffice']),
                             (put_inline, 'SRWEB',  cfg['identity']['srWeb']),
                             (put_inline, 'DRWEB',  cfg['identity']['drWeb']),
                             (put_inline, 'ANIK',   cfg['grs']['anik']),
                             (put_inline, 'APPEAL', cfg['grs']['appeal'])):
            html, done = fn(html, key, val)
            if done:
                marks.append(key)

        c = cfg['compact']
        html = html.replace('--s125-compact: 1;', '--s125-compact: %s;' % c['s125'])
        if 'board' in c:
            html = html.replace('--compact: 1;', '--compact: %s;' % c['board'])
        if '<!--@DEEDS-->' in html:
            html, info = trim_deeds(html, int(cfg.get('deedRows', 9)))
            if info:
                marks.append('deeds %d/%d' % (info[1], info[0]))

        open(os.path.join(dest, out_name), 'w', encoding='utf-8').write(html)
        built.append((out_name, hits, marks))

    print('  ✓ %s  →  out/%s' % (slug, cfg['folder']))
    for n, hits, marks in built:
        if not cfg.get('showClasses', True):
            marks.append('CLASSES off')
        extra = ('  [%s]' % ', '.join(marks)) if marks else ''
        print('      %-52s %3d swaps%s' % (n, hits, extra))
    return True


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    check_only = '--check' in sys.argv

    if not os.path.isdir(TEMPLATES):
        sys.exit('No templates/ folder — put the master HTML files there.')
    configs = sorted(f for f in os.listdir(OFFICES) if f.endswith('.json'))
    if args:
        configs = [f for f in configs if os.path.splitext(f)[0] in args]
        if not configs:
            sys.exit('No such office config: %s' % ', '.join(args))

    print()
    ok = sum(build_office(os.path.join(OFFICES, f), check_only) for f in configs)
    print('\n  %d of %d office(s) %s\n' % (ok, len(configs),
                                           'valid' if check_only else 'built'))
    sys.exit(0 if ok == len(configs) else 1)


if __name__ == '__main__':
    main()
