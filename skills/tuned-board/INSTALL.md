# tuned.board: install

Source: `skills/tuned-board` in the [skills repo](https://github.com/zdzislawbela/skills).

## Install

```sh
git clone https://github.com/zdzislawbela/skills.git
cp -R skills/skills/tuned-board ~/.claude/skills/tuned-board
```

## Update

Remove the old copy first. `cp -R` over an existing folder would keep old files.

```sh
git -C skills pull
rm -rf ~/.claude/skills/tuned-board && cp -R skills/skills/tuned-board ~/.claude/skills/tuned-board
```

## Check

1. Start a new Claude Code session (skills load at start).
2. Type `/skills`. The list should have `tuned-board`.
3. Version: `grep -m1 Version ~/.claude/skills/tuned-board/SKILL.md`.

## Uninstall

```sh
rm -rf ~/.claude/skills/tuned-board
```

Then start a new session. Boards you already published keep working.
