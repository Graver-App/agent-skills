---
name: graver-dataform-workbench
description: Use when working on a Dataform project that is open in Graver (graver.dev) — from Graver's terminal, a `/ide` session, or any MCP client attached to its endpoint. Reach for the `dataform_*` tools instead of the `dataform` CLI: they run through the open workbench, so verdicts, diagnostics and the activity log land where the human is watching, validation is a free dry run that stays correct across un-run upstream changes, and a broken sibling file does not stop the work. Covers orientation, the compile/validate/run loop, per-object runs, protected profiles, staleness, and the action types Graver refuses to run natively.
license: Apache-2.0
metadata:
  source: https://graver.dev
---

# Graver Dataform workbench

## Overview

Graver is a macOS workbench for Looker + Dataform development. It hosts no agent:
you are the agent, brought by the user, and Graver exposes its capabilities to you
as MCP tools over two transports from one registry — the `/ide` WebSocket (what
Claude Code's `/ide` attaches to) and an HTTP endpoint.

**Default to the tools over the CLI.** Not for convenience: the tools answer
questions the CLI cannot, and they put the answer where the human can see it.

## First, confirm you are attached

`graver_ping` is the liveness check. If it is not in your tool list, you are not
attached to a Graver workbench — use the `dataform` CLI in the terminal and say so,
rather than guessing.

Then **`dataform_status` before anything else.** It returns the project root, the
settings file, the run profiles *with what each one does*, which profile is active,
and a compiled-graph summary. Every other tool's behaviour depends on the active
profile, because the profile carries the schema suffix that decides which dataset
you write to. Do not run anything before you have read it.

## The loop

| Step | Tool | Notes |
|---|---|---|
| Orient | `dataform_status` | profiles, active profile, graph summary |
| List | `dataform_list_actions` | every action with type, target, defining file, dependencies, plus declarations |
| Compile | `dataform_compile` | after editing `.sqlx`; the app also compiles on save |
| Validate | `dataform_validate(action)` | BigQuery dry run: free, runs nothing, scans nothing |
| Look at data | `dataform_preview(action, limit)` | `SELECT * LIMIT n`, default 20, max 200 |
| What needs a run | `dataform_staleness` | not built, or built before the code changed |
| Run | `dataform_run(action, include_stale_deps)` | one object; see the refusals below |
| Audit the docs | `dataform_declaration_drift` | every `columns:` block against its query; **expensive, opt-in** |

`action` is always the object's **bare name** (`top_words`), not a path and not a
fully-qualified target.

## Are the `columns:` blocks true?

`dataform_declaration_drift` checks every `columns:` block in the project against
what its query actually produces. The moment to run it is right after a
documentation backfill, which is the moment a block most often starts claiming a
column the query stopped selecting.

It reports two outcomes and they are not the same kind of thing:

- **Phantom** — declared, not produced. **A defect.** Anything reading the block
  believes it. A phantom column is how a column dropped from a query a year ago
  goes on being advertised, and how a tool that trusts the block issues an order
  that cannot work.
- **Undeclared** — produced, not documented. **Not a defect.** `columns:`
  describes; it does not promise completeness. Report it as context — it is what
  makes a declaration weak evidence — not as work.

**It is expensive and that is why it is a separate tool.** One BigQuery dry run
per object that declares columns: free in bytes, nothing scanned, nothing
billed, and minutes of wall clock on a large project. It is never part of
`dataform_validate`, and you should not call it speculatively.

**Read the coverage before quoting the result.** `complete` is false when any
object that claims columns went unchecked, and `notChecked` names the probes
that failed. "No phantoms" and "no phantoms among the objects we got to" are
different answers, and only one of them is in `findings`. Declarations are out
of scope and counted in `declarationsNotInScope`: a declaration has no query of
its own to dry-run, so its block describes a table the project reads rather
than builds.

A phantom is a statement about **this commit's** compiled query, and the tool
infers no intent. A declared column that is gone may be one somebody wants back
— the fix is either the documentation or the query, and that is the human's
call, not yours.

## Why these instead of `dataform` on the command line

Four differences that change answers, not ergonomics:

1. **Validation stays correct across un-run upstream changes.** `dataform_validate`
   does cascaded synthesis: if a dependency changed in code but has not been run,
   its *future* schema is synthesized so the dry run still reflects what the project
   will be. A plain CLI dry run validates against the schema that exists today and
   reports failures for columns that are merely pending.
2. **A broken sibling file does not stop you.** The CLI refuses to run anything while
   the project has any compilation error — verified with both a syntax error and a bad
   `ref()`, with and without `--dry-run`. Graver runs from its cached graph, so one
   unrelated broken file does not block validating or running the object in front of
   you. (The Dataform *web UI* behaves like Graver here, not like the CLI.)
3. **No whole-project compile per command.** The CLI compiles everything on every
   invocation — a second or two on a small project, tens of seconds on a large one.
4. **The human sees it.** Results land in the results grid, diagnostics in the
   diagnostics tab, and every operation in the activity log. A CLI run in a scratch
   terminal leaves the workbench showing stale state, so the person watching has no
   idea what you did.

## Runs are per-object, and that is deliberate

`dataform_run` runs **one action**, optionally preceded by the stale upstream slice
(`include_stale_deps: true`). There is no tag selection and no whole-graph run. Do
not try to simulate one by looping over `dataform_list_actions` — if the user wants
a graph run, the honest answer is the terminal (`dataform run --tags ...`), because
a multi-action run needs a plan shown before it executes, a failure policy, and live
progress that this tool does not have.

**A protected profile refuses the tool outright.** Profiles can be marked protected,
and `dataform_run` is refused for them — the human runs those from the app. Read the
profile from `dataform_status` and do not try to work around it.

## What a native run refuses, and what to do instead

Each refusal names the exact terminal command, so pass it on rather than paraphrasing:

- **`operations` actions** — not supported natively.
- **Unrecognized BigQuery table options.** Anything Graver does not generate stops
  the run, because ignoring a table option would quietly replace a partitioned table
  with an unpartitioned copy of it.
- **Incremental strategies Graver does not implement.** `MERGE` (or unspecified) with
  `onSchemaChange: IGNORE` runs natively; anything else is refused rather than
  guessed at. **Incrementals are not categorically excluded** — check the refusal
  message before telling the user they must use the terminal.

A refusal is a correctness feature. Do not route around one by hand-writing the SQL
and running it yourself.

**There is no full-refresh switch.** How an incremental writes is decided by what is
already in the warehouse, not by a flag you pass: no table yet builds it from the full
query; a table with a unique key is merged, so re-running cannot duplicate rows; a table
with no unique key is appended to, trusting the query's own `when(incremental())` filter.
So "rebuild the incrementals from scratch" is **not expressible here** — that is
`dataform run --actions <name> --full-refresh` in the terminal. Do not run an incremental
through the tool while telling the user it was rebuilt.

## Staleness is a sampled answer

`dataform_staleness` covers the files checked so far — the workbench checks what the
user can see — so it is a map, not a census. For a definitive answer about one
object, call `dataform_validate`.

A staleness verdict is a BigQuery metadata read plus a git timestamp: it compares the
table's `lastModified` against the last commit that touched the defining file, and
treats a dirty file as "changed now". It costs no query and reads no rows. One
consequence worth knowing: an **untracked** file (a freshly renamed `.sqlx`, say) has
no commit to compare against, so git-derived signals cannot speak for it until it is
staged.

## Editing

You have the editor too: `openFile(filePath, startLine, endLine)`,
`getDiagnostics(uri)`, `getOpenEditors`, `getWorkspaceFolders`,
`getCurrentSelection`, and `openDiff(old_file_path, new_file_path, new_file_contents,
tab_name)` which opens the change as a diff tab in Graver. Prefer showing a diff for
anything non-trivial: the person is sitting in front of the editor, and a diff they
can read beats a file that silently changed.

## Formatting

`.sqlx` is not SQL — it carries `config`, `js`, `pre_operations` and
`post_operations` blocks — so formatting needs the Dataform templater.

- `dataform_setup_sqlfluff(force)` makes the templater available. It checks the
  user's own sqlfluff first and only builds a private environment if that one lacks
  the plugin. Use it when formatting reports a missing templater.
- `dataform_create_sqlfluff_config` seeds the project with an editable `.sqlfluff`
  (BigQuery dialect, templater that keeps `${ref()}` intact). It fails if one already
  exists — edit that file instead of forcing it.

## Rules

- **Read `dataform_status` first.** The active profile decides where every write
  lands.
- **Validate before running.** It is free, it is a dry run, and it cascades.
- **Never work around a refusal.** Hand the user the terminal command the refusal
  gives you.
- **One object per run.** No tag loops, no synthetic graph runs.
- **Say which profile you used** when you report a result; "it worked" is ambiguous
  across profiles.
