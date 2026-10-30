(function () {
  // tuned.board · optional code diff panel. Injected by build.py only with --diffs.
  // resizable (drag handle on the left edge), header "Diff kodu · ACn · title", sections Commity / Pliki / Zmiany,
  // follows the AC the viewer opens; scrolling never switches it, a "Pokaż ACn" button offers the card at the top.
  // CFG = {strings, counts: {tileId: commits}, data: {tileId: [commit]} | url: "/_blob/…" (lazy, fetched on first open)}
  // commit = {repo, side: "fe"|"be", sha, subject, files: [{path, status, add, del, test, patch?, skipped?}]}
  const CFG = /*TB:DIFF_CFG*/null;
  const S = CFG.strings;
  const list = document.getElementById('tiles');
  const tiles = [...list.querySelectorAll('li.tile')];
  if (!tiles.length) return;
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
  const store = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* storage off */ } } };

  let data = CFG.data || null, loading = null;
  let open = false, cur = null, commitSha = null, side = 'all', view = store.get('tb-diff-view') === 'split' ? 'split' : 'unified', opener = null;

  // ---- panel skeleton
  const panel = el('aside', 'dp'); panel.id = 'tb-diff'; panel.hidden = true; panel.tabIndex = -1;
  panel.setAttribute('aria-labelledby', 'dp-title');
  const top = el('div', 'dp-top'); const nav = el('div', 'dp-nav');
  const iconBtn = (cls, txt, label) => { const b = el('button', 'dp-icon ' + cls, txt); b.type = 'button'; b.setAttribute('aria-label', label); b.title = label; return b; };
  const prev = iconBtn('dp-prev', '‹', S.prev), next = iconBtn('dp-next', '›', S.next), close = iconBtn('dp-close', '×', S.close);
  const pick = el('select'); pick.setAttribute('aria-label', S.pick);
  tiles.forEach(li => { const o = el('option', null, li.dataset.z + ' · ' + li.dataset.title); o.value = li.dataset.id; pick.append(o); });
  // "Pokaż ACn": the card nearest the top differs from the panel's AC (scrolling never switches the panel by itself)
  const follow = el('button', 'dp-follow'); follow.type = 'button'; follow.hidden = true;
  nav.append(prev, pick, next, follow);
  const hrow = el('div', 'dp-hrow');
  const title = el('h2', 'dp-title'); title.id = 'dp-title'; title.tabIndex = -1;
  hrow.append(title, close);
  const tools = el('div', 'dp-tools');
  const seg = (label, items, get, set) => {
    const g = el('div', 'dp-seg'); g.setAttribute('role', 'group'); g.setAttribute('aria-label', label);
    items.forEach(([v, txt]) => { const b = el('button', null, txt); b.type = 'button'; b.dataset.v = v; b.addEventListener('click', () => { set(v); render(); }); g.append(b); });
    g.sync = () => g.querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.v === get())));
    return g;
  };
  const sideSeg = seg(S.filter, [['all', S.all], ['fe', S.fe], ['be', S.be], ['tests', S.tests]], () => side, v => { side = v; });
  const viewSeg = seg(S.view, [['unified', S.unified], ['split', S.split]], () => view, v => { view = v; store.set('tb-diff-view', v); });
  tools.append(sideSeg, viewSeg);
  // where the code comes from (local checkouts), and that the remote repository is what counts
  const source = el('p', 'dp-src', S.source || '');
  top.append(hrow, nav, source, tools);
  const scroll = el('div', 'dp-scroll');
  const hint = el('p', 'dp-hint', S.hint);
  // drag handle on the left edge (pointer + keyboard), width saved per viewer
  const grip = el('div', 'dp-grip'); grip.tabIndex = 0;
  grip.setAttribute('role', 'separator'); grip.setAttribute('aria-orientation', 'vertical'); grip.setAttribute('aria-controls', 'tb-diff');
  grip.setAttribute('aria-label', S.resize || ''); grip.title = S.resize || '';
  panel.append(grip, top, scroll, hint);
  document.body.append(panel);

  // ---- width: min 360px, max 80% of the window; double-click resets; saved per viewer (storage may be off)
  const W_KEY = 'tb-diff-w', W_MIN = 360, W_STEP = 32;
  const wMax = () => Math.max(W_MIN, Math.round(innerWidth * 0.8));
  let width = parseInt(store.get(W_KEY), 10) || null;
  function setWidth(w, save) {
    width = w == null ? null : Math.min(wMax(), Math.max(W_MIN, Math.round(w)));
    if (width == null) document.documentElement.style.removeProperty('--dp-w');
    else document.documentElement.style.setProperty('--dp-w', width + 'px');
    if (save) store.set(W_KEY, width == null ? '' : String(width));
    const now = Math.round(panel.getBoundingClientRect().width) || width || W_MIN;
    grip.setAttribute('aria-valuemin', String(W_MIN)); grip.setAttribute('aria-valuemax', String(wMax())); grip.setAttribute('aria-valuenow', String(now));
  }
  setWidth(width, false);
  addEventListener('resize', () => { if (width != null) setWidth(width, false); });
  grip.addEventListener('pointerdown', e => {
    if (e.button !== 0) return;
    e.preventDefault(); grip.setPointerCapture(e.pointerId); document.body.classList.add('dp-resizing');
    const move = ev => setWidth(innerWidth - ev.clientX, false);
    const up = () => {
      grip.removeEventListener('pointermove', move); grip.removeEventListener('pointerup', up); grip.removeEventListener('pointercancel', up);
      document.body.classList.remove('dp-resizing'); setWidth(width, true);
    };
    grip.addEventListener('pointermove', move); grip.addEventListener('pointerup', up); grip.addEventListener('pointercancel', up);
  });
  grip.addEventListener('dblclick', () => setWidth(null, true));
  grip.addEventListener('keydown', e => {
    const w = Math.round(panel.getBoundingClientRect().width);
    const to = { ArrowLeft: w + W_STEP, ArrowRight: w - W_STEP, Home: W_MIN, End: wMax() }[e.key];
    if (to == null) return;
    e.preventDefault(); e.stopPropagation(); setWidth(to, true);
  });

  // ---- Diff button in each AC header band (only ACs with commits)
  tiles.forEach(li => {
    if (!CFG.counts[li.dataset.id]) return;
    const b = el('button', 'dp-btn', S.btn); b.type = 'button'; b.dataset.dp = li.dataset.id;
    b.setAttribute('aria-label', S.btnLabel + li.dataset.z); b.setAttribute('aria-controls', 'tb-diff'); b.setAttribute('aria-expanded', 'false');
    const right = li.querySelector('.head-right'); if (right) right.prepend(b);
  });

  // ---- diff renderer (unified + side by side)
  function parse(patch) {
    const rows = []; let o = 0, n = 0;
    for (const line of patch.split('\n')) {
      const h = /^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*)$/.exec(line);
      if (h) { o = +h[1]; n = +h[2]; rows.push({ t: 'hunk', text: line }); continue; }
      const c = line[0];
      if (c === '+') rows.push({ t: 'add', n: n++, text: line.slice(1) });
      else if (c === '-') rows.push({ t: 'del', o: o++, text: line.slice(1) });
      else if (c === '\\') rows.push({ t: 'meta', text: line });
      else if (line !== '') rows.push({ t: 'ctx', o: o++, n: n++, text: line.slice(1) }); // '' = trailing newline, not a context line
    }
    return rows;
  }
  const ln = (v, cls) => `<td class="ln${cls ? ' ' + cls : ''}">${v == null ? '' : v}</td>`;
  function unified(rows) {
    return '<table class="unified"><tbody>' + rows.map(r => {
      if (r.t === 'hunk' || r.t === 'meta') return `<tr class="${r.t}"><td colspan="4">${esc(r.text)}</td></tr>`;
      const s = r.t === 'add' ? '+' : r.t === 'del' ? '−' : '';
      return `<tr class="${r.t}">${ln(r.o)}${ln(r.n)}<td class="s">${s}</td><td class="c">${esc(r.text)}</td></tr>`;
    }).join('') + '</tbody></table>';
  }
  function split(rows) {
    const out = []; let i = 0;
    const mark = t => t === 'add' ? '<span class="sm">+</span>' : t === 'del' ? '<span class="sm">−</span>' : '';
    const cell = (r, k) => r ? `${ln(r[k], r.t === 'ctx' ? '' : r.t)}<td class="c ${r.t === 'ctx' ? '' : r.t}">${mark(r.t)}${esc(r.text)}</td>` : '<td class="ln none"></td><td class="c none"></td>';
    while (i < rows.length) {
      const r = rows[i];
      if (r.t === 'hunk' || r.t === 'meta') { out.push(`<tr class="${r.t}"><td colspan="4">${esc(r.text)}</td></tr>`); i++; continue; }
      if (r.t === 'ctx') { out.push(`<tr>${cell(r, 'o')}${cell(r, 'n')}</tr>`); i++; continue; }
      const dels = [], adds = [];
      while (i < rows.length && rows[i].t === 'del') dels.push(rows[i++]);
      while (i < rows.length && rows[i].t === 'add') adds.push(rows[i++]);
      for (let k = 0; k < Math.max(dels.length, adds.length); k++) out.push(`<tr>${cell(dels[k], 'o')}${cell(adds[k], 'n')}</tr>`);
    }
    return '<table class="split"><tbody>' + out.join('') + '</tbody></table>';
  }
  const counts = f => `<span class="dp-n"><span class="a">+${f.add}</span><span class="d">−${f.del}</span></span>`;
  const sideOf = (c, f) => (f.test ? 'tests' : c.side === 'be' ? 'be' : 'fe');
  const tag = k => S[k + 'Tag'] || S[k];

  // ---- render current AC
  function render() {
    const li = document.getElementById('tile-' + cur);
    title.innerHTML = `${esc(S.panel)} · <span class="znum">${esc(li.dataset.z)}</span> · ${esc(li.dataset.title)}`;
    syncFollow();
    pick.value = cur;
    const idx = tiles.indexOf(li);
    prev.disabled = idx <= 0; next.disabled = idx >= tiles.length - 1;
    sideSeg.sync(); viewSeg.sync();
    document.querySelectorAll('.dp-btn').forEach(b => b.setAttribute('aria-expanded', String(open && b.dataset.dp === cur)));
    if (!data) { scroll.innerHTML = `<p class="dp-msg" role="status">${esc(loading === false ? S.loadFail : S.loading)}</p>`; return; }
    const commits = data[cur] || [];
    // a side (FE / BE) without commits in this AC is said in words, not left out
    const has = new Set(commits.map(c => (c.side === 'be' ? 'be' : 'fe')));
    const noSide = k => `<p class="dp-msg dp-noside">${esc((S.noSide || '').replace('{side}', k.toUpperCase()))}</p>`;
    const gaps = ['fe', 'be'].filter(k => !has.has(k)).map(noSide).join('');
    if (!commits.length) { scroll.innerHTML = `<p class="dp-msg">${esc(S.empty)}</p>` + gaps; return; }
    if (commitSha && !commits.some(c => c.sha === commitSha)) commitSha = null;
    // named sections in the cards' divider style: "Commity (n)", "Pliki (n)", "Zmiany"
    const sec = (label, n) => `<h3 class="divider dp-h">${esc(label)}${n == null ? '' : ` (${n})`}</h3>`;
    let h = `<section class="dp-sec">${sec(S.commits, commits.length)}<ul class="dp-list dp-commits">`;
    h += `<li><button type="button" data-commit="" aria-pressed="${!commitSha}"><span class="t">${esc(S.allCommits)}</span></button></li>`;
    h += commits.map(c => `<li><button type="button" data-commit="${esc(c.sha)}" aria-pressed="${commitSha === c.sha}"><span class="sha">${esc(c.sha)}</span><span class="t">${esc(c.subject)}</span><span class="dp-tag">${esc(tag(c.side === 'be' ? 'be' : 'fe'))}</span></button></li>`).join('');
    h += '</ul>' + gaps + '</section>';
    const files = [];
    commits.filter(c => !commitSha || c.sha === commitSha).forEach(c => c.files.forEach(f => { if (side === 'all' || sideOf(c, f) === side) files.push([c, f]); }));
    h += `<section class="dp-sec">${sec(S.files, files.length)}`;
    if (!files.length) { scroll.innerHTML = h + ((side === 'fe' || side === 'be') && !has.has(side) ? noSide(side) : `<p class="dp-msg">${esc(S.emptyFilter)}</p>`) + '</section>'; return; }
    h += '<ul class="dp-list dp-files">' + files.map(([c, f], k) =>
      `<li><button type="button" data-file="${k}" aria-label="${esc(S.jump + f.path + ', +' + f.add + ' −' + f.del)}"><span class="p">${esc(f.path)}</span><span class="sha">${esc(c.sha.slice(0, 7))}</span>${counts(f)}</button></li>`).join('') + '</ul></section>';
    // + / − are text in each changed line; the legend says what they and the two number columns mean
    h += `<section class="dp-sec dp-changes">${sec(S.changes)}<p class="dp-legend">${esc(S.legend || '')}</p>` + files.map(([c, f], k) => {
      let body = '';
      if (f.skipped && f.skipped !== 'za duży') body = `<p class="dp-note">${esc(S.skipped)}: ${esc(f.skipped)}</p>`;
      else {
        if (f.skipped) body += `<p class="dp-note">${esc(S.tooBig)}</p>`;
        if (f.patch) body += `<div class="dp-code">${(view === 'split' ? split : unified)(parse(f.patch))}</div>`;
      }
      return `<section class="dp-file" id="dp-file-${k}"><div class="dp-fh" tabindex="-1"><span class="p">${esc(f.path)}</span><span class="sha">${esc(c.sha)}</span><span class="dp-tag">${esc(tag(sideOf(c, f)))}</span>${counts(f)}</div>${body}</section>`;
    }).join('') + '</section>';
    scroll.innerHTML = h;
  }

  function load() {
    if (data || loading) return;
    loading = fetch(CFG.url).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(j => { data = j; loading = null; if (open) render(); })
      .catch(() => { loading = false; if (open) render(); });
  }

  // ---- open / close / switch
  function show(id, focus) {
    const changed = id !== cur; cur = id;
    if (changed) { commitSha = null; scroll.scrollTop = 0; }
    if (!open) { open = true; panel.hidden = false; document.body.classList.add('dp-open'); }
    if (!data) load();
    render();
    if (focus) title.focus();
  }
  function hide() {
    if (!open) return;
    open = false; panel.hidden = true; document.body.classList.remove('dp-open');
    document.querySelectorAll('.dp-btn').forEach(b => b.setAttribute('aria-expanded', 'false'));
    const back = (opener && document.contains(opener) && opener.offsetParent !== null) ? opener : document.querySelector(`.dp-btn[data-dp="${cur}"]`);
    if (back) back.focus();
    opener = null;
  }
  const step = d => { const i = tiles.findIndex(li => li.dataset.id === cur) + d; if (i >= 0 && i < tiles.length) show(tiles[i].dataset.id, false); };
  // AC for the "." key: the one highlighted in the index (in view), else the first open one, else the first
  function currentAc() {
    const row = document.querySelector('.ilist li[aria-current="true"]');
    if (row) return row.dataset.id;
    const o = tiles.find(li => !li.classList.contains('folded'));
    return (o || tiles[0]).dataset.id;
  }

  prev.addEventListener('click', () => step(-1));
  next.addEventListener('click', () => step(1));
  close.addEventListener('click', hide);
  pick.addEventListener('change', () => show(pick.value, false));
  scroll.addEventListener('click', e => {
    const cb = e.target.closest('[data-commit]');
    if (cb) { commitSha = cb.dataset.commit && cb.dataset.commit !== commitSha ? cb.dataset.commit : null; render(); return; }
    const fb = e.target.closest('[data-file]');
    if (fb) { const sec = document.getElementById('dp-file-' + fb.dataset.file); if (sec) { sec.scrollIntoView({ block: 'start', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' }); sec.querySelector('.dp-fh').focus({ preventScroll: true }); } }
  });
  panel.addEventListener('keydown', e => {
    if ((e.key === 'ArrowLeft' || e.key === 'ArrowRight') && !e.altKey && !e.metaKey && !e.ctrlKey && !e.shiftKey && !/^(SELECT|INPUT|TEXTAREA)$/.test(e.target.tagName)) {
      e.preventDefault(); step(e.key === 'ArrowLeft' ? -1 : 1);
    }
  });
  // Diff button in an AC header: open on that AC, or close when it is already showing.
  // while the panel is open, a click anywhere in an AC header band (fold, title, chips) switches the panel to it
  list.addEventListener('click', e => {
    const b = e.target.closest('.dp-btn');
    if (b) { if (open && cur === b.dataset.dp) hide(); else { opener = b; show(b.dataset.dp, true); } return; }
    const head = e.target.closest('.head');
    if (head && open) { const li = head.closest('li.tile'); if (li && li.dataset.id !== cur) show(li.dataset.id, false); }
  });
  // Mapa AC rows (they move between state groups, so delegated) and #tile- links
  document.addEventListener('click', e => {
    const a = e.target.closest('.ilist a[href^="#tile-"]');
    if (a && open) show(a.getAttribute('href').slice(6), false);
  });
  addEventListener('hashchange', () => { const li = location.hash.startsWith('#tile-') && document.getElementById(location.hash.slice(1)); if (open && li) show(li.dataset.id, false); });
  // A card opened one at a time (fold button, title, keyboard, link) loses its "folded" class: follow it.
  // "Rozwiń wszystkie" opens many at once and does not switch.
  if ('MutationObserver' in window) new MutationObserver(ms => {
    if (!open) return;
    const opened = ms.filter(m => m.target.matches('li.tile') && /(^|\s)folded(\s|$)/.test(m.oldValue || '') && !m.target.classList.contains('folded')).map(m => m.target);
    if (opened.length === 1 && opened[0].dataset.id !== cur) show(opened[0].dataset.id, false);
  }).observe(list, { subtree: true, attributes: true, attributeFilter: ['class'], attributeOldValue: true });
  // Scrolling keeps the panel's AC; the header offers the card nearest the top instead
  function topCard() { return tiles.find(li => !li.hidden && li.getBoundingClientRect().bottom > 80) || null; }
  function syncFollow() {
    const t = open && topCard();
    follow.hidden = !t || t.dataset.id === cur;
    if (!follow.hidden) { follow.dataset.id = t.dataset.id; follow.textContent = (S.showAc || '{z}').replace('{z}', t.dataset.z); }
  }
  let raf = 0;
  addEventListener('scroll', () => { if (open && !raf) raf = requestAnimationFrame(() => { raf = 0; syncFollow(); }); }, { passive: true });
  follow.addEventListener('click', () => { if (follow.dataset.id) show(follow.dataset.id, false); });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && open && !document.querySelector('.lightbox') && !e.target.closest('.gate-edit')) { hide(); return; }
    if (e.key !== '.' || e.metaKey || e.ctrlKey || e.altKey) return;
    const t = e.target;
    if (/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName) || t.isContentEditable) return;
    e.preventDefault();
    if (open) hide(); else { opener = document.activeElement !== document.body ? document.activeElement : null; show(currentAc(), true); }
  });
})();
