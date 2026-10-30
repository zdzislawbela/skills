#!/usr/bin/env python3
"""Collect the code diff of every AC commit into diffs.json for the optional diff panel.

usage: diffs.py BOARD.json --out DIFFS.json

  Each repo in board.json `repos[]` that has commits needs `path` (local git checkout) and `side` ("fe" | "be").
  For every tile commit: git -C <path> show --no-color --format=%H%x00%s --patch <sha>
  Output: {tileId: [{repo, side, sha, subject, files: [{path, status, add, del, test, patch | skipped}]}]}
  Lockfiles, snapshots, binaries and generated files are listed with `skipped` and no patch.
  A file patch over 150 KB is cut and gets `skipped: "za duży"`.
  The output contains source code: a board built with it is for people inside the organization only.
"""
import argparse, json, os, re, subprocess, sys

MAX_PATCH = 150 * 1024
LOCK = re.compile(r'(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|composer\.lock|Cargo\.lock|poetry\.lock|Gemfile\.lock|go\.sum|npm-shrinkwrap\.json)$')
SNAP = re.compile(r'(\.snap$|(^|/)__snapshots__/)')
GEN = re.compile(r'(\.min\.(js|css)$|\.map$|(^|/)(dist|build|vendor|generated)/|\.generated\.|\.scss\.d\.ts$|\.pb\.go$)')
TEST = re.compile(r'((^|/)(__tests__|tests?|e2e|spec)/|\.(test|spec)\.[jt]sx?$|Test\.php$)', re.I)


def skip_reason(path, block):
    if LOCK.search(path): return 'lockfile'
    if SNAP.search(path): return 'snapshot'
    if GEN.search(path): return 'wygenerowany'
    if re.search(r'^(Binary files|GIT binary patch)', block, re.M): return 'binarny'
    return None


def parse_file(block):
    """block = one `diff --git a/x b/y` section (without the leading 'diff --git ')."""
    head, _, rest = block.partition('\n@@')
    m = re.search(r'^\+\+\+ b/(.+)$', head, re.M) or re.search(r'^rename to (.+)$', head, re.M) or re.search(r'^--- a/(.+)$', head, re.M)
    path = m.group(1) if m else block.split(' b/', 1)[-1].split('\n', 1)[0]
    status = 'added' if 'new file mode' in head else 'deleted' if 'deleted file mode' in head else 'renamed' if 'rename to' in head else 'modified'
    patch = ('@@' + rest) if rest else ''
    lines = patch.split('\n')
    add = sum(1 for l in lines if l.startswith('+'))
    dele = sum(1 for l in lines if l.startswith('-'))
    f = dict(path=path, status=status, add=add, **{'del': dele}, test=bool(TEST.search(path)))
    reason = skip_reason(path, head)
    if reason:
        f['skipped'] = reason
    elif len(patch.encode()) > MAX_PATCH:
        cut = patch.encode()[:MAX_PATCH].decode('utf-8', 'ignore')
        f['patch'] = cut[:cut.rfind('\n')] if '\n' in cut else cut
        f['skipped'] = 'za duży'
    else:
        f['patch'] = patch
    return f


def show(path, sha):
    out = subprocess.run(['git', '-C', path, 'show', '--no-color', '--diff-merges=first-parent', '--format=%H%x00%s', '--patch', sha],
                         capture_output=True, text=True, errors='replace')
    if out.returncode:
        sys.exit(f'git show {sha} in {path} failed: {out.stderr.strip()}')
    first, _, body = out.stdout.partition('\n')
    full, _, subject = first.partition('\x00')
    blocks = re.split(r'^diff --git ', body, flags=re.M)[1:]
    return full, subject, [parse_file(b) for b in blocks]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('board')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    B = json.load(open(a.board, encoding='utf-8'))
    repos = {r['id']: r for r in B.get('repos', [])}
    defs = {c['sha']: c for t in B['tiles'] for c in t.get('commits', []) if isinstance(c, dict)}
    cache, out = {}, {}
    for t in B['tiles']:
        lst = []
        for c in t.get('commits', []):
            c = defs[c] if isinstance(c, str) else c
            r = repos.get(c.get('repo'), {})
            if not r.get('path'):
                sys.exit(f'repo {c.get("repo")!r} (commit {c["sha"]}) has no "path" in board.json repos[]')
            if c['sha'] not in cache:
                full, subject, files = show(os.path.expanduser(r['path']), c['sha'])
                cache[c['sha']] = dict(repo=r['id'], side=r.get('side', r['id']), sha=c['sha'], full=full, subject=subject, at=c.get('at', ''), files=files)
            lst.append(cache[c['sha']])
        out[t['id']] = sorted(lst, key=lambda x: x['at'])
    text = json.dumps(out, ensure_ascii=False, separators=(',', ':'))
    open(a.out, 'w', encoding='utf-8').write(text)
    nf = sum(len(c['files']) for c in cache.values())
    sk = sum(1 for c in cache.values() for f in c['files'] if f.get('skipped'))
    print(f'diffs: {len(cache)} commits · {nf} files ({sk} skipped/cut) · {len(text.encode()) // 1024} KB -> {a.out}')


if __name__ == '__main__':
    main()
