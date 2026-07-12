---
description: Append a new entry to docs/roadmap/CHANGELOG.md from recent work
argument-hint: [short title for this batch of work]
allowed-tools: Bash(git log:*), Bash(git status:*), Bash(git diff:*), Bash(date:*), Read, Edit
---

Append an entry to the project changelog at `docs/roadmap/CHANGELOG.md`. That file is the
only changelog — do not create another one anywhere else.

Today's date: !`date "+%B %d"`

Recent commits (most recent first):
!`git log --oneline -15`

Uncommitted changes right now:
!`git status --short`

File-level diff of uncommitted changes:
!`git diff --stat HEAD`

## How this repo's changelog works (match it exactly)

- Read `docs/roadmap/TONE.md` first and write in that voice: everyday words, short
  sentences, real file names and real numbers. Read it out loud before you save.
- Newest first. Add your section at the **top**, under the intro paragraph, above the
  existing dated sections.
- Section heading: `## <Month Day> — <short title>` (e.g. `## July 12 — Codex brain live`).
  Use `$ARGUMENTS` as the title if given; otherwise write a plain one from the changes.
- Second line names the session so the transcript can be found later, in the same shape
  as existing entries: `Manager session: Claude Code \`<id>\` (<model>, <role>).` If you
  are a worker session and don't have that, say so plainly instead of inventing an ID.
- Then bullets: one per meaningful change. Each says what happened, why it matters, and
  where the evidence lives (a path, a command and its real output, a proof file). No
  proof, no "done".

## Task

1. Work out what's new since the last logged entry, using the commits and working-tree
   changes above. Skip anything already in the changelog.
2. Write the section and prepend it to `docs/roadmap/CHANGELOG.md`.
3. Lead with anything broken, in flight, or waiting on Kartik — never "all routine"
   while a known problem is open.
4. Don't invent changes you can't see in the git output. If nothing is worth logging,
   say so and change nothing.

Reminders (from ORCHESTRATION.md), but do **not** act on them unless I ask:
- Everyone works on main; pull before you push.
- Update the mission-control page before every git push. A changelog entry is not a
  substitute for it.
Do not commit or push from this command.
