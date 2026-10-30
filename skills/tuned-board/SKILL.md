---
name: tuned-board
description: Build and publish a "tuned.board": a shared Artifact page for one ticket that shows the work actually done, split into ACs (one AC = one acceptance criterion / slice of functionality, numbered AC1…ACn), each with a category, plain before/now text, a Dev checklist with proof, a click-through frames player, PM/Design/QA checklists, a self-service Team checklist (DEV, QA, PM, Design, Merged), a switch chip, note and discussion stored in the artifact db. Use this whenever the user asks for a board, tuned.board, QA/PM handover page, sign-off page or "show what's done" page for a ticket, or wants to update or republish an existing board, add an AC (tile), re-record frames or reseed its db.
---

# tuned.board

**Version 1.0.2** (see `CHANGELOG.md`). The header label shows "tuned.board v1.0.2" (`VERSION` in
`scripts/build.py`). Install, update and uninstall: `INSTALL.md`.

## What is an AC (rule)

An AC is **only a functional acceptance criterion**: a change in the product that has implementing code and tests.
Docs and process items are **not ACs**:

- Handbook, guide, write-up → board.json `documentation` → section **Dokumentacja** in Stan tablicy (link + status,
  no sign-offs).
- Process (push, MR, merge rule, "test after push") → `repos[]` fields in **Gdzie to jest** (`status`, `merge`,
  `afterPush`).

`build.py` prints a `WARNING` (the build still runs) for a tile with `category: "docs"` and for a tile whose Commit step
is `"na"` (no code). When you take an item off the AC list, do not renumber the others: AC numbers stay as they were
(set `"ac"` when a gap appears). Its db doc stays in the db; the page only renders tiles that are in board.json.

A board is generated from one `board.json` by `scripts/build.py`. The engine
(`assets/template.html`) does all the live parts in the browser: sign-offs, gate,
note, discussion, Mapa AC. You only write the board content and run the build.

UI language is Polish by default; set `"language": "en"` in board.json for English (`assets/strings.json`). This
file names sections by their Polish labels; the English labels are in the `en` block of the same file.

## Terms (shown on the page as a legend)

- **AC** = one acceptance criterion: one slice of the ticket, one card on the board.
  Each AC has a stable number `AC1…ACn` (its position in `tiles[]`, or `"ac": N`).
  The card header, section dividers ("AC3 · Co sprawdzić"), note and discussion all
  carry the number, so comments can point at it. Do not renumber: append new ACs at the end or
  set `"ac"` explicitly. The JSON key stays `tiles[]` and the tile `id` stays the db doc id.
- **Dev checklist** = what the developer did: Analiza, Poprawka, Commit, Test.
  One pill per step in the card's header band. Dev pills are not sign buttons: a click opens the
  step's proof (state, date, text, proof link/log/commits) in a small area under the two rows.
- **Co sprawdzić** = per-role instructions for PM, Design and QA, in its own block.
- **Team checklist** = the sign-off pills, labelled by role: DEV, QA, PM, Design, then Merged
  last. Bugfix ACs get "Błąd potwierdzony" first. A signed pill shows who + day small inside
  (full time in the tooltip); click signs, second click undoes.
- **Pills** (both rows): same size, shape and marks, as text: ✓ done/signed, ▶ current, ○ open,
  – n/a, ! done without proof.
- **Foldable cards**: each AC is a bordered card (shadow in light theme, 48px apart)
  with a filled header band, see "Card layout". The body folds with the
  ▸/▾ button (`aria-expanded`) or a click on the title. **Collapsed by default**, so the
  page reads as a list of AC headers; "Rozwiń wszystkie / Zwiń wszystkie" at the top;
  a Mapa AC row click or a `#tile-<id>` link opens the AC. Open state is remembered per
  viewer in localStorage (`tb-open:<ticket>`; ignored when storage is off).
- **Section dividers**: inside an open AC every section has a labelled divider with the
  AC number: "AC3 · Co się zmienia", "Jak to działa", "Co sprawdzić", "Szczegóły techniczne",
  "Notatka", "Dyskusja".
- **Kategoria** = every AC shows "Kategoria: Nowa funkcja | Usprawnienie | Poprawka błędu" (neutral tint, never alarm
  red). "docs" is not an AC category; it is only the category of `documentation` items.
- **Mapa AC** (left sidebar) = every AC's Dev checklist and Team checklist in one compact row; see "Page layout".
  When Dev checklist is done and DEV is unsigned, the DEV pill gets a small dot and the words
  "Dev checklist zrobiony — kliknij DEV, żeby potwierdzić" as tooltip and `aria-describedby` (no extra line).
- **Włącznik** = what turns the change on: "Włącznik: brak", "Włącznik: flaga FE NAME",
  "Włącznik: flaga BE NAME", "Włącznik: ustawienie name". It sits in the body under
  "Szczegóły techniczne". Clicking the chip opens the editor (stored in db `gate`).

- **One box per AC, no nested boxes.** The AC card is the only bordered box. Inside
  it: "Co sprawdzić" is plain lists under small PM / Design / QA headings (QA numbered,
  then "Oczekiwane:"); Dev checklist and Team checklist are pill rows in the header band
  (the Dev proof area is a filled strip with a left rule, not a box); the note is a
  plain one-line input; the discussion is a plain list. Frame players keep their image
  frame, nothing more. Sections are separated only by the labelled dividers. Keep it
  this way when changing the engine.

## Card layout

Header band (always visible, also folded), nothing else in it:

```
[▸] AC3  Title                       Kategoria: …     [Diff] [Gotowe do scalenia]
Dev checklist   [✓ Analiza] [✓ Poprawka] [✓ Commit] [▶ Test]
Team checklist  [○ DEV] [○ QA] [○ PM] [○ Design] [○ Merged]   (bugfix: [○ Błąd potwierdzony] first)
(Dev pill clicked: "Poprawka · zrobione · date", text, proof)
```

- One short state word in the title row: "Gotowe do scalenia" or "Scalone"; nothing while waiting.
  No "Czeka na: …" chip, no "Podpisali / Bez podpisu" ticks, no "Dev checklist: następny krok" chip, no
  "Następnie: …" line, no Team checklist section at the bottom.
- Phone (≤ 600px): label above its pills; fold, AC pill and title share the first line.
- Body order: Co się zmienia (with "AC w zgłoszeniu") · Jak to działa · Co sprawdzić · Szczegóły techniczne
  (Włącznik chip + note + editor, "aktualizacja", "Notatki dla devów", commits) · Notatka · Dyskusja.

## Page layout

Top to bottom: header (ticket, version label, title, intro, legend), "Gdzie to jest", then two columns on laptop
(≥ 1100px), one column on phone (Mapa AC first). Section names are fixed:

1. **Mapa AC** (left sidebar, 384px, sticky on laptop; full width on phone). Only legend + rows, no counts.
   - Heading "Mapa AC", subtitle "Stan każdego AC. Kliknij, żeby przejść."
   - Legend once: "✓ zrobione · ▶ teraz · ○ brak · – nie dotyczy" (" · ! zrobione bez dowodu" added only when
     some step is done without proof).
   - Column header once: "Dev checklist: A·P·C·T  Team checklist: DEV·QA·PM·Des·M". Its `title` (and screen-reader text) says
     "A = Analiza, P = Poprawka, C = Commit, T = Test, Des = Design, M = Merged".
   - Rows grouped by state, small subheading with count: "W toku (Dev checklist) · n" (Dev checklist not finished),
     "Czeka na podpisy · n", "Gotowe do scalenia · n", "Scalone · n". Empty groups hidden; tile order kept.
   - Row line 1: "ACn · <short>" (`short` from board.json, else `title`; ellipsis; full title on hover).
   - Row line 2: Dev checklist segments ✓A ✓P ✓C ▶T, thin separator, Team chips (filled + ✓ signed, outlined + ○ not).
   - Row line 3 only when it adds information: "Gotowe do scalenia", "Scalone", or "Czeka na: QA" when partly
     signed. Nobody signed = no line (the group heading says it).
   - Click: opens the AC and scrolls to it; with the diff panel open, the panel switches too.
2. **Stan tablicy** (main column, one box): "Dev checklist skończony: X z N AC", "Podpisy: DEV x/N · …",
   "Pokaż tylko:" filters with counts, "Kto ma się jeszcze podpisać" as a table role → AC ranges ("AC1–AC5, AC7"),
   then the board's `waiting` list ("Czeka na <owner>") as a plain block with a purple left rule, then
   **Dokumentacja**: one line per `documentation` item (link, status under it), grey left rule, no sign-offs.
3. **Lista AC** (main column): heading, "Rozwiń wszystkie / Zwiń wszystkie", the AC cards.

Marks are always text (✓ ▶ ○ – !), colour only supports them. Contrast at least 4.5:1 in both themes.

## What a board is (and is not)

- It shows **work actually done** on a ticket. One AC = one slice of functionality,
  so PM/Design/QA comments land on the right piece. Bugs found during work are ACs
  with `"category": "bugfix"`.
- Per AC: plain **Co się zmienia / Przed / Teraz** text, **Dev checklist** with proof,
  **documentation** as an animated frames player, **Co sprawdzić w ACn** (PM, Design,
  QA: steps + expected result), **Team checklist**, Włącznik chip, note, discussion,
  and a **Szczegóły techniczne** section for the technical detail.

## Writing AC text (rule)

Write for someone who uses the product and never saw its code. Main text = three short sentences, each
under ~15 words, concrete (name the screen and the button):

- `change` "Co się zmienia": what changes for the reader.
- `before` "Przed": what they saw before.
- `now` "Teraz": what they see now.

Example (cache):
> Co się zmienia: zapisane ustawienia szybciej pokazują się w aplikacji.
> Przed: po kliknięciu Save aplikacja mogła długo pokazywać stare ustawienia.
> Teraz: nowe ustawienia widać najpóźniej po 15 sekundach.

No developer terms in the title, `short`, main text or checklists (no BFF, cache,
config, revalidate, TTL, null, flag, patch, field names). Checklists follow the same
style: screen + button + what you should see. Anything technical (field names, flags,
db checks, SQL, branch names) goes into `dev` (folded "Notatki dla devów" under "Szczegóły techniczne").
For a new feature where nothing existed, "Przed" says so plainly. If you are not sure
what the user saw before, ask instead of guessing.
- Header "Gdzie to jest": one row per repo (branch, MR, head commit, pushed/local,
  test env). No git history columns anywhere; commits appear only as collapsible
  proof inside an AC. Process facts live here, not in an AC: `status` ("gotowe do wysłania (lokalnie)"),
  `merge` ("commit po commicie, bez squasha"), `afterPush` ("QA na środowisku MR").
- Wide screens: Mapa AC on the left (see "Page layout").

Sign-off keys are stored in db and must stay stable (labels are display only):
`tester` "Błąd potwierdzony" (bugfix ACs only), `dev` "DEV", `verified` "QA",
`pm` "PM", `design` "Design", `merged` "Merged" (created on first click).
`progress` ("W toku") is no longer shown; old values stay in db and are ignored.
Each person clicks their own button; it stores `{by, at}` and shows who + when.
Second click undoes. State: Merged signed = "Scalone"; all other buttons signed =
"Gotowe do scalenia"; otherwise waiting (no word on the card; Mapa AC and Stan tablicy say "Czeka na: …"). The Mapa AC Team chips show DEV · QA · PM · Des · M
(`dev`, `verified`, `pm`, `design`, `merged`; bugfix adds "Błąd" = `tester`).

## Files

- `scripts/build.py` – board.json → page HTML + db seed (`write_db` batch entries).
  Run with `-h` for options.
- `scripts/diffs.py` – board.json → diffs.json (code of every AC commit) for the diff panel.
- `scripts/record.mjs` – Playwright-in-Docker recorder for click-through frames (red ring
  on what gets clicked). It holds one example scenario for a made-up app: copy it for yours.
- `scripts/preview.mjs` – renders a built page outside claude.ai with the seed data: laptop and phone, both themes.
- `assets/` – `template.html` engine, `player.js/css`, `diffpanel.js/css` (diff panel), `strings.json`. Edit only to
  change the engine for every board.
- `references/ui-quality-indicators.md` – what makes a board screen good (see "Quality loop").
- `examples/template-board.json` – fake "Porządki po imprezowym weekendzie" board (house party clean-up; no pet is ever to blame) that uses every field
  except `frames`, and every state. Start a new board by copying it. Without `frames` each shot shows a dashed slot.
- `README.md` – what it is and how to start. `INSTALL.md` – install, update, check and uninstall.

## board.json in short

Read `examples/template-board.json` for the full shape. Key fields:

- `ticket {key,title,url}`, `intro`, `pageTitle`, `qaEnv`, `language`. The header always adds the engine's
  "Po co ta tablica" / "Jak się podpisać" line under `intro`, so `intro` only needs to say what the ticket is about.
- `team {dev, qa, pm, design}` (optional) – first names behind each role. Used in "Czeka na: DEV (Basia)" and in the
  overview list "Kto ma się jeszcze podpisać"; without it the roles show without names.
- `repos[]` – rows of "Gdzie to jest": `id,name,branch,note,mr,mrUrl,head,pushed,env,envNote`. Optional:
  `status` (text of the Wysłane pill; colour still from `pushed`), `merge` ("Scalanie: …" under the branch),
  `afterPush` ("Test po wysłaniu: …" under the env), `envLabel` (short name in AC QA headings; default `side` in
  capitals, else `name`). `env` is the repo's test environment (FE "localhost:3000", BE "localhost:8000 + testy
  jednostkowe BE"); `localhost:PORT` and `http(s)://` values become links.
- `documentation {title?, items[]}` (optional) – Dokumentacja in Stan tablicy. Item: `label`, `url`, `status`,
  optional `category` (only `"docs"` allowed). No sign-offs, no db.
- `frames {anim, captions, assets}` (optional) – folder with `<shot>-<n>.jpg`, `captions.tsv`
  (`<shot>-<n><TAB>caption`), and the assets map (`"<file>:<bytes>": "<uploaded url>"`).
  Optional `stills` folder for single images (`<shot>-*.png|jpg`).
- `tiles[]` (one entry per AC) – `id` (stable, it is the db doc id), optional `ac`
  (number override), optional `env` (list of repo ids and/or plain text; the QA heading shows
  "QA sprawdza · FE: localhost:3000 · BE: localhost:8000 + testy jednostkowe BE"; without it, board `qaEnv`),
  `category` (`feature|improvement|bugfix`, required; `docs` only warns, see "What is an AC"; legacy
  `"kind": "bug"` still means bugfix), `short`, `title`, optional `ticketAc` (text of the
  matching AC from the ticket, shown small under the title), `change`, `before`, `now`
  (legacy `what` still renders when these are absent), `dev` (string or list, folded
  "Szczegóły techniczne"), `next`,
  `gate {type: fe-flag|be-flag|config|none|unknown, name, note}` (chip text
  "Włącznik: …"; `none` reads "Włącznik: brak", `unknown` "Włącznik: jeszcze nie ustalony"; the engine adds how to
  switch the change off per type before `note`),
  `steps {analysis,test[,fix,commit]}` each `{state, at, text?, proof {kind: log|link|asset, label, value}}`,
  `commits[]` (object `{sha,title,at,repo,branch?,pushed?}` or a sha string defined in
  another tile; fix/commit/test steps are derived from them),
  `shots [[id, caption]]`, `checklists {pm[], design[], qa {steps[], expect}}`.
- Seed-only (applied only on a brand-new board): `seedSignoffs {key: {by,name,at}}`,
  `seedNote`, `seedMessages [{tile,author,at,text}]`, gate `by/name_by/at`.
- Inline text supports `` `code` `` and `**bold**` only.

## Workflow

1. **Content.** Write/extend `board.json`. Follow "Writing AC text" above; describe
   the slice, not the history. Every AC needs a category, code + tests, QA steps + expected result, and `env`.
   Docs → `documentation`; push / MR / merge rule → `repos[]`.
2. **Frames.** Record (`record.mjs`, Docker) or generate frames into the `anim` folder and add
   captions. Frames must not be real customer data on a template.
3. **Build** (from the skill folder):
   ```
   python3 scripts/build.py BOARD.json --out PAGE.html --seed SEED.json --seed-files DIR [--db-dump DUMP] [--embed-missing] [--diffs DIFFS.json]
   ```
   Without the assets map entries the build fails and lists missing frames; that
   protects against shipping a multi-MB page. `--embed-missing` inlines them as
   data: URIs (fine for small placeholder frames).
4. **Publish.** Load `artifact-design` and `artifact-capabilities` first. Capabilities
   are always `{"assets":{},"db":{},"user":{"scopes":["profile"]}}`.
   - New board: publish without `url`, `icon: "board"`.
   - Existing board: `Artifact read` the url first, then publish to the same `url`.
     Keep capabilities as they are.
5. **Frames upload (real boards).** `upload_asset` the frames (`file_paths`, up to 25
   per call), add `"<file>:<bytes>": url` to the assets map, rebuild, republish.
   Re-recorded frames have a new size, so they need a new upload.
6. **Seed the db.**
   - New board: the seed is all `set`. Send `DIR/batch.json` (entries with `file_path`)
     as `writes` of `write_db` `db_op: "batch"` (max 50 writes per call; split if more).
   - Existing board: **never `set` an existing item**; people's sign-offs, notes and
     messages live there. First dump it:
     `read_db` `db_op: "list"`, `collection: "items"`, `out_dir: DIR`, then rebuild with
     `--db-dump DIR`. Existing tiles become `update` writes that touch only `agent.steps`
     (and the gate while nobody edited it); new tiles become `set`. Messages are not
     seeded for an existing board. If the steps in the build equal the dump, skip the write.
7. **Code diff panel (optional).** See "Code diff panel" below.
8. **Check** the published page: header rows, every AC, player runs, Mapa AC Dev checklist and
   Team marks match the cards, notes and messages show, no "brak dowodu" where proof exists.
   Before every publish, also go through "Quality check before publishing" below.

## Quality check before publishing

Go through this list before every publish (new board, engine change or content change):

- **Contrast** at least 4.5:1 for all text, including the 11–12px labels (dividers, ticks,
  pills, dates, diff line numbers), in both light and dark theme.
- **Phone, 390px wide**: no sideways scroll anywhere except code (diff panel, proof logs).
- **AC state in words**, never colour only ("Gotowe do scalenia", "Scalone"; Mapa AC "Czeka na: …").
- **✓ ▶ ○ – ! as text** (not only an icon or a colour), in Mapa AC and both checklist rows.
- **One language:** the board's `language`. Exceptions that stay as they are: AC, Dev checklist, Team checklist,
  Merged, Diff.
- **One box per AC**: no nested bordered boxes inside a card.
- **No contradictions** between the AC state, Dev checklist and Team checklist. A Dev checklist step
  shown as done needs proof, unless the step itself says why there is none.
- **Przed / Teraz** are plain sentences for a non-technical reader (see "Writing AC text").

Contrast check: read the token pairs in `assets/template.html` and `assets/diffpanel.css` (text colour on its surface,
both themes) with a WCAG contrast calculator.

## Quality loop

Every engine change goes through these steps, in order:

1. **Change** the engine or the content.
2. **Own screenshots.** Build `examples/template-board.json` with `--seed-files DIR` and `--embed-missing`, then run
   `scripts/preview.mjs` (Playwright; see the file's header for the Docker command). It shoots laptop 1280×800 and
   phone 390×844, light and dark. Look at every shot and fix what looks wrong; repeat at most twice.
3. **Optional outside rating.** Rate the shots with a person or a scoring tool of your own, such as Jev. Indicators:
   `references/ui-quality-indicators.md` (clear, act, honest, copy, fit; at most 16 words per sentence; state in
   words; main thing first).

## Code diff panel (optional)

Like GitHub's "." view: a **Diff** button in each AC header band (only ACs with commits) or
the **.** key opens a panel on the right with the code of that AC. The board narrows to the
left; on a phone the panel is a full-screen overlay with a close button. Inside: header
"ACn · title", commit list (sha + subject, click = only that commit), file list with +/−
counts (click scrolls to the file), Jeden widok / Obok siebie (unified / split), filter
Wszystko / FE / BE / Testy, AC switcher (‹ ›, select, ←/→ while the panel has focus).
Header: "Diff kodu · ACn · title", close, AC switcher, then the source caption; sections "Commity (n)",
"Pliki (n)", "Zmiany" in the cards' divider style. While the panel is open, a click in an AC header band, opening
a card, its Diff button, a Mapa AC row or a `#tile-` link switches the panel to that AC ("Rozwiń wszystkie" does
not). Scrolling never switches it; a "Pokaż ACn" button in the header offers the card nearest the top. Resize:
drag the left edge (or focus it, ←/→ by 32px, Home/End), 360px to 80% of the window, double-click resets, width
saved per viewer in localStorage `tb-diff-w`; phone overlay is full screen. Esc or × closes and returns focus. Both themes, reduced motion respected, no external libraries.
Under the title: "Podgląd z lokalnych gałęzi. Źródło prawdy: zdalne repozytorium." When the AC has no BE (or FE) commits, the
panel says "BE: brak zmian w tym AC" (or FE) instead of leaving it out.

**The board then contains source code. Share it only inside the organization.**

1. Each repo in `repos[]` with commits needs `path` (local checkout) and `side` (`fe`|`be`):
   ```
   {"id": "fe", "path": "~/code/my-app", "side": "fe", ...}
   ```
2. Collect the diffs (keep the file next to the board's frames, not in the skill folder):
   ```
   python3 scripts/diffs.py BOARD.json --out DIR/<TICKET>.diffs.json
   ```
   Lockfiles, snapshots, binaries and generated files are listed as "pominięty" without code;
   a file patch over 150 KB is cut ("za duży").
3. Build with `--diffs DIR/<TICKET>.diffs.json`.
   - Under 300 KB: embedded in the page.
   - 300 KB or more: the build stops and asks for an upload. `upload_asset` the file
     (`file_path`, a call of its own) to the board's artifact, add
     `"<TICKET>.diffs.json:<bytes>": "/_blob/..."` to the assets map, rebuild. The page fetches
     it on the first panel open. New commits = new size = new upload.
4. Publish as usual (read first, keep capabilities).

Entries in diffs.json for tiles no longer on the board are ignored when empty (so an uploaded diffs.json stays valid
after an item leaves the AC list); non-empty ones still stop the build.

**No panel:** rebuild without `--diffs` and republish (no Diff button, no "." key).

## Rules

- Do not touch other people's artifacts; publish only to the board's own url.
- Never commit `.token` or real login tokens into recorder scripts or board files.
- Commits stay inside tiles (collapsed). If someone asks for a commit history
  column, push back: the board is about slices of work, not git.
- When a tool call is refused or hangs, stop and report; don't work around it.
- POC stays labelled POC. If the ticket, sprint goal or plan says POC, or the work is built to a POC
  standard (shortcuts, hand-rolled state, repo READMEs, skills or CLAUDE.md rules skipped), the MR title
  starts with `POC:` and the board header says POC. Drop the label only after the code is brought up to
  the repo standard, and say so in the MR description. Never remove POC from the title just to mark the MR
  ready: reviewers then review a POC as production code.
