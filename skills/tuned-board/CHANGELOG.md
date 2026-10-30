# tuned.board changelog

## 1.0.2 (2026-10-30)

- First public version: works for any app and any ticket system.
- `ticketAc` is the name of the field with the ticket's AC text.
- `scripts/record.mjs` holds one example scenario; a login token is optional and comes only from the environment.
- New `scripts/preview.mjs`: shots of a built page outside claude.ai.
- Fixed: an empty strip showed under the Team checklist of every card.
- `path` in `repos[]` may start with `~`. The build time on the page is local time.

## 1.0.1 (2026-10-29)

- Rule: POC work keeps `POC:` in the MR title and board header until the code meets the repo standard.

## 1.0 (2026-10-19)

First stable version. The skill builds and publishes a tuned.board: a shared Artifact page for one ticket.

- One card per AC (acceptance criterion with code and tests), numbered AC1…ACn, with a category, plain
  "Co się zmienia / Przed / Teraz" text, "Jak to działa" frames player and "Co sprawdzić" lists for PM, Design and QA.
- Two rows of pills in each card header: Dev checklist (Analiza, Poprawka, Commit, Test, each with proof) and
  Team checklist (DEV, QA, PM, Design, Merged; bug fixes add "Błąd potwierdzony"). One click signs with name and date,
  a second click undoes. Sign-offs, notes and discussion live in the artifact db.
- Page parts: "Gdzie to jest" (repos, branches, MR, test environment, merge rule), Mapa AC (state of every AC in one
  row), Stan tablicy (counts, who still has to sign, "Czeka na …", Dokumentacja), Lista AC.
- Docs and process items are not ACs: docs go to Dokumentacja, push / MR / merge rule to "Gdzie to jest".
- Optional code diff panel (`--diffs`, "Diff" button or the "." key): commits, files, unified or side by side view.
- `scripts/build.py` builds the page and the db seed from `board.json`; `scripts/diffs.py` collects diffs;
  `scripts/record.mjs` records click-through frames. `examples/template-board.json` shows the full board.json shape.
- Polish UI, both themes, phone layout, text marks (✓ ▶ ○ – !) so state never depends on colour alone.
- Install, update and uninstall: `INSTALL.md`.
