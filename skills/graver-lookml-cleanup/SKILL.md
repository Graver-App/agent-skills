---
name: graver-lookml-cleanup
description: Use when auditing or cleaning up a LookML project — broken fields, views and explores nothing reaches, dashboards that will fail — with Graver (graver.dev), through either the `looker_validate` MCP tool or the `graver-lookml` CLI. Covers the order to run the loop in (validate, triage, fix what is charted, diff, re-validate) and the rules that keep a cleanup honest: only git is visible so "on no dashboard" means defer rather than delete, "no longer reported" is not "fixed", and a check that was skipped is not a check that passed.
license: Apache-2.0
metadata:
  source: https://graver.dev
---

# LookML cleanup with Graver

## Overview

Graver validates a **whole** LookML project — the check Looker itself performs only
when a query happens to use a broken field. It parses every file, resolves includes,
`extends`, refinements and `@{constants}`, and reports unresolved `${view.field}`
references, fields referencing a view their explore does not join, and (given a
BigQuery project) every field's SQL dry-run against the warehouse.

**It calls no Looker API and needs no Looker credentials.** The project is a folder
with `manifest.lkml` in it. Warehouse checks use local application-default
credentials and are dry runs: nothing is scanned, nothing is billed, no rows are read.

Two surfaces, same engine:

- **`looker_validate`** over MCP, when Graver is running. It needs no open project —
  validating LookML is a pure function of a folder, so `path` is an argument.
- **`graver-lookml`**, a headless CLI with the same engine, for a machine that can reach
  the warehouse but cannot run a GUI. It is built from the Graver repository rather than
  installed with the app, so if it is not on your PATH, use the MCP tool; the flags below
  are listed because the two surfaces take the same options under different names.

## Run it in this order

```
1. looker_validate(path, bigquery_project, index, triage: true)   → save the JSON
2. read blastRadius, then triage.dashboardsWithProblems           → fix what is charted
3. edit
4. looker_validate(..., diff_from: "<the saved JSON>")            → prove what moved
```

| MCP argument | CLI flag | What it adds |
|---|---|---|
| `path` *(required)* | the positional folder | the project to read |
| `bigquery_project` | `--bigquery-project` | per-field dry runs; **without it the field-level rejections — most of the work — never run**, and the report says "(local checks only)" |
| `index` | `--index` | a page in the repo that links the dashboards that matter (e.g. `documents/home.md`); failing fields on those are flagged |
| `triage` | `--triage` | the work order: grouped by cause, dashboards to open, what nothing reaches |
| `looker_url` | `--looker-url` | makes the work order's dashboard links clickable; **implies triage** |
| `diff_from` | `--diff` | compare against a saved earlier run |
| `format` | *(markdown is the default; `--json` for data)* | `json` is the MCP default |

The CLI also takes `--connection-default <project.dataset>` (what Looker's connection
points at, from Looker Admin ▸ Connections). Without it, views with no
`sql_table_name` cannot be resolved and land in `unvalidatableViews` — a large
unvalidatable count usually means this is wrong, not that the project is broken.

## Read these keys, in this order

1. **`blastRadius`** — `failingFields`, `onADashboard`, `onNoDashboard`, and the
   `index` breakdown. The split, not the total, is what decides whether anyone's
   afternoon is cancelled. One failing field a dashboard charts outranks two hundred
   that nothing charts.
2. **`triage.dashboardsWithProblems`** — each entry separates `chartsFailingFields`
   (it will break) from `reachableFailingFields` (it *could*, through its explore),
   plus `shouldReproduce` and `linkedFromIndex`. Reachability alone is close to
   useless: on a real project two dashboards charted a failing field while a hundred
   more could reach one.
3. **`triage.failingFieldsByView`** — **one entry per cause, not per instance.** A
   view whose table was replaced shows up as one group with a count, not as 72
   separate findings. Make the two decisions the group represents; do not make 72
   edits.
4. **`warehouse.rejected`** — per-finding `dashboards`, `inherited`, `declaringView`,
   `file`, `line`, and BigQuery's verbatim `message`.
5. **`triage.brokenViewsNoDashboardReaches`** and **`triage.unusedExplores`** — the
   latent debt. Read the caveat below before touching any of it.

`inherited` + `declaringView` are how you avoid the classic mistake: a broken field
in a mixin shows up in every view that extends it. Fix the declaring view once.

## The rules that keep it honest

**Only what is in git is visible.** Dashboards and Looks built in the Looker UI are
not in the repository, so Graver cannot see them. Every "nothing reaches this" answer
therefore means **defer**, never **delete**. The report ships this caveat inline; do
not strip it when you summarise.

**Read what was *not* checked before deleting anything:**

- `warehouse.checkedAs` and `warehouse.identityCaveat` — Looker reaches BigQuery as
  the service account on its connection. These checks used different credentials, so
  **a table this identity cannot see reads as missing.** A field is not broken because
  you could not see its table.
- `referenceCoverage.fieldsSkippedForLiquid` — Liquid is never guessed at. Those
  fields are unchecked, not clean.
- `warehouse.unvalidatableViews` — same: unchecked.

**"No longer reported" is not "fixed".** The diff deliberately does not say *fixed*.
A finding leaves the report when someone fixes it, when whatever exposed it is
removed (retire an explore and its missing joins vanish while the view still
references views nothing joins), or when it simply was not checked this run. Two
reports cannot tell those apart.

**Read `diff.warnings` before believing `diff`.** They name the ways the numbers
mislead: a baseline that checked no warehouse, a run that checked none, two runs that
checked as **different identities**, a missing corpus stamp, a baseline that is not a
report, Liquid skips moving. Pointing one warehouse recording at another once
reported ninety-seven findings gone with nothing fixed at all.

**A check that stopped looking is not a cleanup.** If failures drop *and*
`fieldsChecked` drops, fields were removed rather than fixed. That may be what was
asked for; it is not the same thing.

## Proving a cleanup

Keep the first run's JSON as the baseline, **outside the project** — a findings
document names client tables. Then every re-run takes `diff_from` (or `--diff`) and
reports `gone`, `new`, `changed`, `unchanged`, each one named, with `counts.findings`
before and after. `changed` is the category that matters most while you work: same
field, different message — you fixed one column and it now fails on the next.

Each document is stamped with the `corpus` it ran against (name, commit, dirty), so a
diff can say which commits it spans and warns when it cannot.

## Don't

- **Don't delete on "unused".** See the git caveat. Defer, and tell the user what you
  deferred.
- **Don't quote the total as the headline.** Quote the split.
- **Don't treat a group as a list of edits.** `failingFieldsByView` is causes.
- **Don't re-run without `diff_from`** once you have a baseline. An un-diffed re-run
  makes the human compare two reports by eye, which is the job this replaces.
