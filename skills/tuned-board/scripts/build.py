#!/usr/bin/env python3
"""Build a tuned board page and its db seed from one board.json.

usage: build.py BOARD.json --out PAGE.html --seed SEED.json [--db-dump DIR] [--embed-missing] [--diffs DIFFS.json]

  BOARD.json      board definition (see examples/template-board.json); relative paths resolve from its folder
  --out           page to publish with the Artifact tool
  --seed          write_db batch entries for the `items` collection
  --db-dump DIR   folder written by Artifact read_db (collection items, out_dir=DIR): tiles that already
                  exist become partial updates of board-owned fields only (steps; gate while nobody edited it).
                  Sign-offs, notes and messages are never written for existing tiles. Without it every tile is a
                  full `set`: use that only for a brand-new board.
  --seed-files DIR also write each seed document to DIR/<collection>.<doc_id>.json and DIR/batch.json
                  (the batch with file_path entries), ready to paste into write_db db_op "batch"
  --embed-missing frames not in the assets map are embedded as data: URIs (default: build fails and lists them,
                  so a forgotten upload never ships a multi-MB page)
  --diffs         diffs.json from scripts/diffs.py: adds the code diff side panel (optional; "Diff" button,
                  "." key). Under 300 KB it is embedded; bigger needs "<file>:<bytes>": "/_blob/..." in the assets map
                  (upload_asset the file to the board artifact), the page fetches it on first panel open.
                  Without --diffs there is no panel. With it the page contains source code: org-internal only.
"""
import argparse, base64, glob, html, json, os, re, sys
from datetime import datetime

VERSION = '1.0.2'

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(SKILL, 'assets')
e = html.escape


def read(p):
    return open(p, encoding='utf-8').read()


def inline(text):
    """Tiny inline format for board text: `code` and **bold**; everything else is escaped."""
    out = e(text)
    out = re.sub(r'`([^`]+)`', r'<code>\1</code>', out)
    out = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('board')
    ap.add_argument('--out', required=True)
    ap.add_argument('--seed', required=True)
    ap.add_argument('--db-dump')
    ap.add_argument('--embed-missing', action='store_true')
    ap.add_argument('--seed-files')
    ap.add_argument('--diffs')
    a = ap.parse_args()

    base = os.path.dirname(os.path.abspath(a.board))
    rel = lambda p: p if not p or os.path.isabs(p) else os.path.join(base, p)
    B = json.load(open(a.board, encoding='utf-8'))
    lang = B.get('language', 'pl')
    strings = json.load(open(os.path.join(ASSETS_DIR, 'strings.json'), encoding='utf-8'))
    if lang not in strings:
        sys.exit(f'language {lang!r} not in assets/strings.json (have: {", ".join(strings)})')
    T = dict(strings[lang]); T.update(B.get('strings', {}))
    ticket = B['ticket']

    # ---- frames: anim/<shot>-<n>.jpg (player) > stills/<shot>-*.jpg|png (still) > dashed slot
    fr = B.get('frames', {})
    anim, stills = rel(fr.get('anim', '')), rel(fr.get('stills', ''))
    caps = {}
    cap_file = rel(fr.get('captions', '')) if fr.get('captions') else (os.path.join(anim, 'captions.tsv') if anim else '')
    if cap_file and os.path.exists(cap_file):
        for line in open(cap_file, encoding='utf-8'):
            if '\t' in line:
                k, v = line.rstrip('\n').split('\t', 1); caps[k] = v
    amap_path = rel(fr.get('assets', ''))
    amap = json.load(open(amap_path)) if amap_path and os.path.exists(amap_path) else {}
    missing, report = [], []

    def uri(path):
        key = f'{os.path.basename(path)}:{os.path.getsize(path)}'  # a re-recorded frame has a new size, so it needs a new upload
        if key in amap:
            return amap[key]
        missing.append(key)
        mime = 'image/png' if path.lower().endswith('.png') else 'image/jpeg'
        return f'data:{mime};base64,' + base64.b64encode(open(path, 'rb').read()).decode()

    def shot_html(shot, cap):
        figcap = f'<figcaption>{e(cap)} · <code>{e(shot)}</code></figcaption>'
        frames = sorted(glob.glob(os.path.join(anim, shot + '-*.jpg')), key=lambda f: int(re.search(r'-(\d+)\.jpg$', f).group(1))) if anim else []
        frames = [f for f in frames if re.search(r'-\d+\.jpg$', f)]
        if frames:
            imgs, steps = [], []
            for i, f in enumerate(frames):
                st = caps.get(os.path.splitext(os.path.basename(f))[0], '')
                imgs.append(f'<img class="frame" src="{uri(f)}" alt="{e(cap)}, {e(T["frameStep"])} {i + 1}: {e(st)}"{"" if i == 0 else " data-off"}>')
                steps.append(f'<li>{e(st)}</li>')
            report.append(f'{shot}: player {len(frames)}')
            return (f'<figure data-shot="{e(shot)}" class="player"><div class="stage">{"".join(imgs)}</div>'
                    f'<div class="pbar"><button type="button" class="pbtn prev" aria-label="{e(T["prev"])}">&#8249;</button>'
                    f'<button type="button" class="pbtn pp" aria-label="{e(T["pause"])}">&#10074;&#10074;</button>'
                    f'<button type="button" class="pbtn next" aria-label="{e(T["nextFrame"])}">&#8250;</button>'
                    f'<span class="pcount">1 / {len(frames)}</span></div><ol class="psteps">{"".join(steps)}</ol>{figcap}</figure>')
        st = (sorted(glob.glob(os.path.join(stills, shot + '-*.jpg'))) + sorted(glob.glob(os.path.join(stills, shot + '-*.png')))) if stills else []
        if st:
            report.append(f'{shot}: still {os.path.basename(st[0])}')
            return f'<figure data-shot="{e(shot)}"><div class="stage"><img src="{uri(st[0])}" alt="{e(cap)}" loading="lazy"></div>{figcap}</figure>'
        report.append(f'{shot}: MISSING')
        return f'<figure data-shot="{e(shot)}"><div class="slot">{e(T["slot"].replace("{id}", shot))}</div>{figcap}</figure>'

    # ---- commits: per tile, a string refers to a commit defined (as an object) in another tile
    repos = {r['id']: r for r in B.get('repos', [])}
    commit_defs = {}
    for t in B['tiles']:
        for c in t.get('commits', []):
            if isinstance(c, dict):
                commit_defs[c['sha']] = c
    def tile_commits(t):
        out = []
        for c in t.get('commits', []):
            sha = c if isinstance(c, str) else c['sha']
            if sha not in commit_defs:
                sys.exit(f'tile {t["id"]}: commit {sha} is referenced but not defined in any tile')
            out.append(commit_defs[sha])
        return sorted(out, key=lambda c: c.get('at', ''))
    def is_pushed(c):
        return bool(c.get('pushed', repos.get(c.get('repo'), {}).get('pushed', False)))
    def log(cs):
        return '\n'.join(f'{c["sha"]}  {c["title"]}  [{c.get("branch") or repos.get(c.get("repo"), {}).get("branch", "")}]' for c in cs)

    # ---- steps: analysis/test from the board; fix/commit derived from commits unless given; "auto" derives explicitly
    def derive_steps(t, cs):
        given = dict(t.get('steps', {}))
        code = [c for c in cs if not c['title'].startswith('test')]
        tests = [c for c in cs if c['title'].startswith('test')]
        fixes = [c for c in code if c['title'].startswith('fix')] or code
        local = '' if all(is_pushed(c) for c in cs) else (' · ' + T['local'])
        auto = {}
        if fixes:
            auto['fix'] = dict(state='done', at=fixes[-1].get('at'), proof=dict(kind='log', value=log(fixes), label=f'{T["stepFix"].lower()} ({len(fixes)})'))
        if cs:
            auto['commit'] = dict(state='done', at=cs[-1].get('at'),
                                  text=', '.join(c['sha'] for c in cs[:3]) + (' …' if len(cs) > 3 else ''),
                                  proof=dict(kind='log', value=log(cs), label=f'{T["stepCommit"].lower()} ({len(cs)}){local}'))
        if tests:
            auto['test'] = dict(state='done', at=tests[-1].get('at'), proof=dict(kind='log', value=log(tests), label=f'{T["stepTest"].lower()} ({len(tests)})'))
        out = {}
        for k in ('analysis', 'fix', 'commit', 'test'):
            v = given.get(k)
            if v == 'auto' or (v is None and k in ('fix', 'commit')):
                v = auto.get(k)
            out[k] = v or dict(state='todo')
        return out

    # ---- static HTML
    # an AC is a functional acceptance criterion with code and tests. Docs and process items are not ACs:
    # they go to board.json `documentation` (Stan tablicy) or to `repos[]` (Gdzie to jest). "docs" still builds, with a warning.
    CATEGORIES = ('feature', 'improvement', 'bugfix', 'docs')
    warnings = []
    tiles_html, index_rows, cfg_tiles, seeds, znums = [], [], {}, [], {}
    for pos, t in enumerate(B['tiles'], 1):
        tid = t['id']
        assert re.fullmatch(r'[A-Za-z0-9_-]{1,60}', tid), f'bad tile id {tid!r}'
        # AC number: stable acceptance-criterion number shown everywhere (default = position; set "ac" when reordering or inserting)
        z = f'AC{int(t.get("ac", pos))}'
        if z in znums:
            sys.exit(f'tile {tid}: {z} already used by tile {znums[z]}')
        znums[z] = tid
        # category for every tile; legacy "kind": "bug" means bugfix
        cat = t.get('category') or ('bugfix' if t.get('kind') == 'bug' else None)
        if cat not in CATEGORIES:
            sys.exit(f'tile {tid}: category must be one of {"|".join(CATEGORIES)} (got {cat!r})')
        if cat == 'docs':
            warnings.append(f'{z} ({tid}): category "docs" is not an AC. Move it to board.json "documentation" (Stan tablicy → Dokumentacja).')
        cs = tile_commits(t)
        steps = derive_steps(t, cs)
        if (steps.get('commit') or {}).get('state') == 'na':
            warnings.append(f'{z} ({tid}): Commit is "nie dotyczy", so this AC has no code. An AC needs code and tests; '
                            'docs go to "documentation", process items (push, MR, merge rule) to "repos[]".')
        gate = t.get('gate') or {'type': 'unknown', 'name': '', 'note': ''}
        cfg_tiles[tid] = dict(steps=steps, gate=gate)
        seeds.append((tid, steps, gate, t))
        # plain text for a non-technical reader: change / before / now; legacy `what` still renders
        parts = ['<div class="desc">']
        if any(t.get(k) for k in ('change', 'before', 'now')):
            # the "Co się zmienia" divider labels the change line, so it carries no inline label
            parts += [f'<p class="what {k}">' + ('' if k == 'change' else f'<b>{e(T[k])}</b> ') + f'{inline(t[k])}</p>' for k in ('change', 'before', 'now') if t.get(k)]
        elif t.get('what'):
            parts.append(f'<p class="what">{inline(t["what"])}</p>')
        if t.get('next'):
            parts.append(f'<p class="next"><b>{e(T["next"])}</b> {inline(t["next"])}</p>')
        parts.append('</div>')
        # body order: Co się zmienia · Jak to działa · Co sprawdzić · Szczegóły techniczne (Włącznik, notes, commits)
        tech = '<div class="gate-slot"></div>'
        dev = t.get('dev')
        if dev:
            dev = [dev] if isinstance(dev, str) else dev
            tech += (f'<details class="sec dev"><summary>{e(T["devTitle"])}</summary><ul class="dev-list">'
                     + ''.join(f'<li>{inline(x)}</li>' for x in dev) + '</ul></details>')
        if cs:
            items = ''.join(
                f'<li><span class="sha">{e(c["sha"])}</span><span class="t">{e(c["title"])}</span>'
                f'<span class="cm">{e(c.get("branch") or repos.get(c.get("repo"), {}).get("branch", ""))}'
                f'{" · " + e(T["local"]) if not is_pushed(c) else ""}</span></li>' for c in reversed(cs))
            tech += f'<details class="sec commits-wrap"><summary>{e(T["commitsTitle"])} · {len(cs)}</summary><ul class="commit-list">{items}</ul></details>'
        shots = t.get('shots', [])
        if shots:
            figs = ''.join(shot_html(*(s if isinstance(s, (list, tuple)) else (s['id'], s.get('caption', '')))) for s in shots)
            parts.append(f'<section class="docs-wrap"><h3 class="divider">{e(T["docsTitle"])}</h3><div class="shots">{figs}</div></section>')
        ch = t.get('checklists', {})
        lis = lambda xs: ''.join(f'<li>{inline(x)}</li>' for x in xs)
        qa = ch.get('qa', {})
        qa_steps, qa_expect = (qa.get('steps', []), qa.get('expect', '')) if isinstance(qa, dict) else (qa, '')
        # test environment per AC: `env` lists repo ids ("FE: localhost:3000") or plain text; fallback board qaEnv
        tenv = t.get('env')
        tenv = [tenv] if isinstance(tenv, str) else (tenv or [])
        envs = []
        for x in tenv:
            r = repos.get(x)
            if r is None:
                envs.append(x)
            elif r.get('env'):
                envs.append(f'{r.get("envLabel") or (r.get("side") or "").upper() or r["name"]}: {r["env"]}')
            else:
                sys.exit(f'tile {tid}: env refers to repo {x!r}, which has no "env"')
        env = ' · '.join(envs) or B.get('qaEnv', '')
        cols = ''
        if ch.get('pm'):
            cols += f'<div class="check-col"><h3>{e(T["pmChecks"])}</h3><ul>{lis(ch["pm"])}</ul></div>'
        if ch.get('design'):
            cols += f'<div class="check-col"><h3>{e(T["designChecks"])}</h3><ul>{lis(ch["design"])}</ul></div>'
        if qa_steps:
            nums = ''.join(f'<li><span class="n">{i}.</span> {inline(x)}</li>' for i, x in enumerate(qa_steps, 1))
            cols += (f'<div class="check-col qa"><h3>{e(T["qaChecks"])}{' · <span class="qenv">' + e(env) + '</span>' if env else ""}</h3><ol class="num">{nums}</ol>'
                     + (f'<p class="expect"><b>{e(T["expect"])}</b> {inline(qa_expect)}</p>' if qa_expect else '') + '</div>')
        if cols:
            parts.append(f'<section class="checks-wrap"><h3 class="divider">{e(T["checksTitle"].replace("{z}", z))}</h3><div class="checks">{cols}</div></section>')
        parts.append(f'<section class="tech-wrap"><h3 class="divider">{e(T["secDev"])}</h3>{tech}</section>')
        tiles_html.append(f'      <li class="tile" id="tile-{tid}" data-id="{tid}" data-z="{z}" data-title="{e(t["title"])}" data-category="{cat}"{' data-ticket-ac="' + e(t["ticketAc"]) + '"' if t.get("ticketAc") else ""}>\n'
                          f'        <div class="body">{"".join(parts)}</div>\n      </li>')
        # Mapa AC row: line 1 "ACn · short title"; line 2 Dev checklist segments + Team chips; line 3 state only when it
        # adds information. Filled and grouped by state live by the engine.
        index_rows.append(f'<li data-id="{tid}"><a href="#tile-{tid}" title="{z} · {e(t["title"])}">'
                          f'<span class="il1"><span class="znum">{z}</span> · {e(t.get("short") or t["title"])}</span>'
                          f'<span class="il2"><span class="iflow"></span><span class="isep" aria-hidden="true"></span><span class="iteam"></span></span>'
                          f'<span class="ist"></span></a></li>')

    built = datetime.now().strftime('%d.%m.%Y, %H:%M')
    header = (f'  <header>\n    <div class="hrow"><span class="key"><a href="{e(ticket.get("url", "#"))}">{e(ticket["key"])}</a> · {e(T["subtitle"])}</span>'
              f'<span class="tb-build">tuned.board v{VERSION} · {e(T['built'])} {built}</span></div>\n'
              f'    <h1>{e(ticket["title"])}</h1>\n    <p class="sub">{inline(B.get("intro") or T["intro"])}</p>\n    <p class="howto">{inline(T["purpose"])}<br>{inline(T["howToSign"])}</p>\n    <p class="legend">{inline(T["legend"])}</p>\n  </header>')
    rows = ''
    for r in B.get('repos', []):
        mr = (f'<a href="{e(r["mrUrl"])}">{e(r.get("mr") or "MR")}</a>' if r.get('mrUrl') else e(r.get('mr') or '—'))
        # optional `status` text replaces the pill word (colour still from `pushed`)
        state = (f'<span class="pill">{e(r.get("status") or T["pushed"])}</span>' if r.get('pushed')
                 else f'<span class="pill local">{e(r.get("status") or T["local"])}</span>')
        envs = r.get('env', '')
        if re.match(r'https?://', envs):
            env_html = f'<a href="{e(envs)}">{e(envs)}</a>'
        elif re.match(r'localhost:\d+$', envs):
            env_html = f'<a href="http://{e(envs)}">{e(envs)}</a>'
        else:
            env_html = e(envs)
        if r.get('envNote'):
            env_html += f'<span class="rnote">{inline(r["envNote"])}</span>'
        if r.get('afterPush'):
            env_html += f'<span class="rnote"><b>{e(T["repoAfterPush"])}</b> {inline(r["afterPush"])}</span>'
        cl = lambda k: f'<span class="cl">{e(T[k])}: </span>'
        rows += (f'<tr><th scope="row">{e(r["name"])}</th><td class="mono">{cl("colBranch")}{e(r["branch"])}'
                 + (f'<span class="rnote">{inline(r["note"])}</span>' if r.get('note') else '')
                 + (f'<span class="rnote"><b>{e(T["repoMerge"])}</b> {inline(r["merge"])}</span>' if r.get('merge') else '')
                 + f'</td><td>{cl("colMr")}{mr}</td><td class="mono">{cl("colHead")}{e(r.get("head", ""))}</td><td>{cl("colState")}{state}</td><td>{cl("colEnv")}{env_html}</td></tr>')
    where = (f'  <section class="where" aria-labelledby="where-h">\n    <h2 id="where-h">{e(T["whereTitle"])}</h2>\n    <div class="scroll"><table>'
             f'<thead><tr><th scope="col">{e(T["colRepo"])}</th><th scope="col">{e(T["colBranch"])}</th><th scope="col">{e(T["colMr"])}</th>'
             f'<th scope="col">{e(T["colHead"])}</th><th scope="col">{e(T["colState"])}</th><th scope="col">{e(T["colEnv"])}</th></tr></thead>'
             f'<tbody>{rows}</tbody></table></div>\n  </section>') if rows else ''
    # Mapa AC: heading, one-line subtitle, legend once, column header once, rows grouped by state (engine)
    index = (f'  <nav class="index" aria-labelledby="idx-h">\n    <h2 id="idx-h">{e(T["indexTitle"])}</h2>\n'
             f'    <p class="isub">{e(T["indexSub"])}</p>\n    <p class="ileg" id="idx-leg">{e(T["indexLegend"])}</p>\n'
             f'    <p class="icols" title="{e(T["idxAbbr"])}"><span class="visually-hidden">{e(T["idxAbbr"])}</span><span aria-hidden="true">{e(T["idxCols"])}</span></p>\n'
             f'    <div class="igroups" id="idx-groups"><ol class="ilist">{"".join(index_rows)}</ol></div>\n  </nav>')
    waiting = ''
    if B.get('waiting', {}).get('items'):
        w = B['waiting']
        waiting = (f'    <section class="owner" aria-labelledby="own-h">\n      <h3 id="own-h">{e(w.get("title", ""))}</h3>\n      <ol>'
                   + ''.join(f'<li>{inline(x)}</li>' for x in w['items']) + '</ol>\n    </section>')
    # Dokumentacja in Stan tablicy: handbooks, guides. Link + status, no sign-offs (not an AC)
    docs_sec = ''
    dsec = B.get('documentation') or {}
    if dsec.get('items'):
        lis_d = ''
        for n, d in enumerate(dsec['items'], 1):
            if d.get('category', 'docs') != 'docs':
                sys.exit(f'documentation item {n}: category must be "docs" (got {d.get("category")!r})')
            name = f'<a href="{e(d["url"])}">{e(d["label"])}</a>' if d.get('url') else e(d['label'])
            lis_d += f'<li><span class="dname">{name}</span>' + (f'<span class="dstat">{inline(d["status"])}</span>' if d.get('status') else '') + '</li>'
        docs_sec = (f'    <section class="docsec" aria-labelledby="docsec-h">\n      <h3 id="docsec-h">{e(dsec.get("title") or T["docsSecTitle"])}</h3>\n'
                    f'      <p class="dsub">{e(T["docsSecSub"])}</p>\n      <ul>{lis_d}</ul>\n    </section>')
    footer = ''
    if B.get('links') or B.get('outOfScope'):
        footer = '    <section class="side-sec" aria-label="' + e(T['linksTitle']) + '">\n'
        if B.get('links'):
            footer += f'      <h2>{e(T["linksTitle"])}</h2>\n      <div class="links">' + ''.join(f'<a href="{e(l["url"])}">{e(l["label"])}</a>' for l in B['links']) + '</div>\n'
        if B.get('outOfScope'):
            footer += f'      <h2>{e(T["outTitle"])}</h2>\n      <ul>' + ''.join(f'<li>{inline(x)}</li>' for x in B['outOfScope']) + '</ul>\n'
        footer += '    </section>'

    # ---- optional code diff panel
    # Mapa AC sidebar + Stan tablicy / Lista AC in the main column (every board); the diff panel stays optional
    version, diff_css, diff_js, diff_note = VERSION, '', '', 'none'
    if a.diffs:
        dpath = os.path.abspath(a.diffs)
        raw = open(dpath, 'rb').read()
        D = json.loads(raw)
        unknown = sorted(k for k in set(D) - set(cfg_tiles) if D[k])
        if unknown:
            sys.exit(f'diffs: tiles not on the board: {", ".join(unknown)}')
        dcfg = dict(strings=T['diff'], counts={k: len(v) for k, v in D.items() if v and k in cfg_tiles})
        if len(raw) < 300 * 1024:
            dcfg['data'] = D; diff_note = f'embedded {len(raw) // 1024} KB'
        else:
            key = f'{os.path.basename(dpath)}:{len(raw)}'
            if key in amap:
                dcfg['url'] = amap[key]; diff_note = f'lazy {amap[key]} ({len(raw) // 1024} KB)'
            elif a.embed_missing:
                dcfg['data'] = D; diff_note = f'embedded {len(raw) // 1024} KB (--embed-missing)'
            else:
                sys.exit(f'diffs {len(raw) // 1024} KB >= 300 KB: upload_asset {dpath} to the board artifact, add "{key}": "<url>" to the assets map, rebuild')
        diff_css = read(os.path.join(ASSETS_DIR, 'diffpanel.css'))
        js = read(os.path.join(ASSETS_DIR, 'diffpanel.js'))
        assert js.count('/*TB:DIFF_CFG*/null') == 1
        diff_js = '<script>\n' + js.replace('/*TB:DIFF_CFG*/null', json.dumps(dcfg, ensure_ascii=False).replace('<', '\\u003c')) + '</script>'
    config = dict(ticket=ticket['key'], strings={k: v for k, v in T.items() if k != 'diff'}, tiles=cfg_tiles, team=B.get('team', {}))
    cfg_json = json.dumps(config, ensure_ascii=False).replace('</', '<\\/')
    page = read(os.path.join(ASSETS_DIR, 'template.html'))
    subs = {
        '<!--TB:TITLE-->': e(B.get('pageTitle') or f'{ticket["key"]} tuned.board'),
        '/*TB:PLAYER_CSS*/': read(os.path.join(ASSETS_DIR, 'player.css')) + '.visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }\n',
        '/*TB:PLAYER_JS*/': read(os.path.join(ASSETS_DIR, 'player.js')),
        '/*TB:CONFIG*/null': cfg_json,
        '<!--TB:HEADER-->': header, '<!--TB:WHERE-->': where, '<!--TB:INDEX-->': index,
        '<!--TB:LOADING-->': e(T['loading']), '<!--TB:WAITING-->': waiting, '<!--TB:DOCS-->': docs_sec,
        '<!--TB:STATE_H-->': e(T['stateTitle']), '<!--TB:LIST_H-->': e(T['listTitle']),
        '<!--TB:TILES-->': '\n'.join(tiles_html), '<!--TB:FOOTER-->': footer,
        '<!--TB:VERSION-->': f'tuned.board v{version}', '/*TB:DIFF_CSS*/': diff_css, '<!--TB:DIFF_JS-->': diff_js,
    }
    for k, v in subs.items():
        assert page.count(k) == 1, f'template placeholder {k} found {page.count(k)}x'
        page = page.replace(k, v)
    if missing and not a.embed_missing:
        sys.exit('frames not in the assets map (upload them, add "<name>:<size>": "<url>" to the map, rebuild; or pass --embed-missing):\n  ' + '\n  '.join(missing))
    open(a.out, 'w', encoding='utf-8').write(page)

    # ---- db seed (items only; messages and sign-offs belong to people)
    existing = {}
    if a.db_dump:
        for f in glob.glob(os.path.join(a.db_dump, 'items', '*.json')):
            existing[os.path.splitext(os.path.basename(f))[0]] = json.load(open(f, encoding='utf-8'))
    STEP_KEYS = ('state', 'text', 'proof', 'at')
    writes = []
    for tid, steps, gate, t in seeds:
        last = max([s.get('at') or '' for s in steps.values()] or [''])
        if tid not in existing:
            data = dict(note=t.get('seedNote', ''), signoffs=t.get('seedSignoffs', {}), gate=gate, agent=dict(steps=steps, at=last or None))
            writes.append(dict(op='set', collection='items', doc_id=tid, data=data))
            continue
        old = existing[tid]
        # every step key written explicitly, absent ones deleted, so no stale text/proof survives a merge
        st = {k: {f: (v[f] if f in v and v[f] is not None else {'__delete__': True}) for f in STEP_KEYS} for k, v in steps.items()}
        patch = dict(agent=dict(steps=st, at=last or {'__delete__': True}))
        og = old.get('gate') or {}
        if not og.get('by') and {k: og.get(k, '') for k in ('type', 'name', 'note')} != {k: gate.get(k, '') for k in ('type', 'name', 'note')}:
            patch['gate'] = dict(type=gate.get('type', 'unknown'), name=gate.get('name', ''), note=gate.get('note', ''))
        writes.append(dict(op='update', collection='items', doc_id=tid, data=patch))
    # demo/imported discussion: only for a brand-new board (with --db-dump the messages belong to people already)
    if not a.db_dump:
        for n, m in enumerate(B.get('seedMessages', [])):
            writes.append(dict(op='set', collection='messages', doc_id=f'seed-{n + 1}',
                               data=dict(item=m['tile'], by=m.get('by', 'imported'), importedAuthor=m['author'], at=m['at'], text=m['text'], source=m.get('source', ''))))
    orphan = sorted(set(existing) - {s[0] for s in seeds})
    json.dump(writes, open(a.seed, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if a.seed_files:
        d = os.path.abspath(a.seed_files); os.makedirs(d, exist_ok=True)
        batch = []
        for w in writes:
            f = os.path.join(d, f'{w["collection"]}.{w["doc_id"]}.json')
            json.dump(w['data'], open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            batch.append(dict(op=w['op'], collection=w['collection'], doc_id=w['doc_id'], file_path=f))
        json.dump(batch, open(os.path.join(d, 'batch.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print('shots:', '; '.join(report) or 'none')
    print('embedded (not in assets map):', len(missing), ' '.join(missing))
    print(f'tuned.board v{version} · diffs: {diff_note}')
    print(f'page {len(page.encode()) // 1024} KB · tiles {len(seeds)} · seed writes {len(writes)} '
          f'({sum(w["op"] == "set" for w in writes)} set, {sum(w["op"] == "update" for w in writes)} update)')
    if orphan:
        print('db tiles not on the board (left untouched, not shown on the page):', ', '.join(orphan))
    for w in warnings:
        print('WARNING:', w, file=sys.stderr)
    if len(writes) > 50:
        print('NOTE: write_db batch takes max 50 writes; split the seed file')


if __name__ == '__main__':
    main()
