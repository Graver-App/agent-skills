---
name: graver-audit-report
description: Use when turning a Graver findings document (the JSON from `looker_validate`, `graver-lookml --json`, or `--declaration-sweep --json`) into something a person or an agent can act on — publishing it as a report, a shareable page or an artifact, or producing a prioritised checklist of the exact problems to work on. Covers which keys answer which question, how to derive a stable id per problem so two runs can be compared, and the gate that must run first: a document from a replayed recording can be stale, and the report has to say so instead of reading like a live run.
license: Apache-2.0
metadata:
  source: https://graver.dev
---

# Publishing a Graver audit, and the checklist that comes out of it

## Overview

Graver's validators write a **document**, not a report. `looker_validate` and
`graver-lookml --json` describe a whole LookML project; `--declaration-sweep --json`
describes a Dataform project's `columns:` declarations against what its queries
actually produce. Both group findings by cause, which is the right shape for a
machine and the wrong shape for someone deciding what to do on a Tuesday.

This skill is about the second step: reading one of those documents and producing
either a published report or a checklist of discrete work items.

**It runs nothing.** The input is a file a previous run wrote. If no such file
exists yet, use `graver-lookml-cleanup` (whole LookML project),
`graver-dataform-workbench` (a Dataform project) or `graver-looker-view-reconcile`
(one view) to produce one, then come back. Do not edit LookML or `.sqlx` from this
skill either — a report is a report. The cleanup skills own the edits and the rules
about which edits are safe.

## Before anything else: is this document current?

A document may come from a replay of a recorded warehouse session, and a recording
answers only for the commits it was taken against. Replayed against a project that
has moved, it reports brand-new fields as failures and answers others from recorded
probes of a sibling table. **Neither looks like staleness; both look like findings.**

Read `replay` first. It is always present:

```json
"replay": {
  "replayed": true,
  "recording": "project-both-abc1234.json",
  "recordedLookML": "looker @ abc1234",
  "recordedDataform": "warehouse @ def5678",
  "pinsAgree": false,
  "caveats": ["warning: LookML corpus has moved since this recording: ..."],
  "derivedCalls": 1,
  "unmatchedCalls": 0
}
```

- `"replayed": false` — the warehouse answered directly. Nothing to qualify.
- `replayed` true and `pinsAgree` true — the recording is of the tree the document
  describes. Say which recording, and move on. Even then, check `unmatchedCalls`: a
  LookML recording carries the Dataform cross-check's dry runs only if it was made
  with `--dataform-project`, and without them every field needing one reaches no
  verdict for a reason that has nothing to do with the project.
- **`pinsAgree` false — do not publish a report that reads as current.** Put the
  `caveats` at the top of the page, before the findings, in the reader's path. They
  are whole sentences already; do not summarise them into "some caveats apply".
- `unmatchedCalls` above zero means some fields were reported as failures because the
  recording had no answer for them. Those are not findings about the project. If this
  is large relative to the finding count, the honest report is "re-record", not a list.
- `pinsAgree` is false for *unknown* as well as for *mismatched* — a recording with no
  pin, or a folder that is not a checkout. Unknown is not agreement. The `caveats`
  say which case it was.

An older document may lack the `replay` key entirely. That is not "it was live": it
is a document from a binary that did not report this. Say so.

## Which key answers which question

### How much is wrong, and how much of it matters

`summary` is one line of counts. The number that decides urgency is in `blastRadius`:

| Key | Means |
|---|---|
| `blastRadius.onADashboard` | failing fields a dashboard **in this repository** charts |
| `blastRadius.onNoDashboard` | failing fields nothing in the repository reaches |
| `blastRadius.index.failingFieldsOnALinkedDashboard` | of those, the ones on a dashboard the project's own index page links |
| `blastRadius.caveat` | why "on no dashboard" is not "unused" — see the refusals below |
| `blastRadius.byKind` | what the total is made of: `rejected`, `unresolvedReference`, `notJoined` |

A real project can report 240 failing fields of which **one** is on a charted
dashboard. A report that leads with 240 has buried its own answer. Lead with the
split, and order the checklist by it.

#### `failingFields` is a union of three checks — use `byKind`

`blastRadius.failingFields` counts distinct `view.field` across BigQuery
rejections, unresolved references **and** fields whose explore lacks a join it
needs. `byKind` breaks that down disjointly — first match wins, so the values
sum to the total.

Two consequences, and both have produced a wrong report:

- **`triage.failingFieldsByView` lists the rejections only.** A project that has
  fixed every rejection leaves it empty while the headline is still non-zero.
  The rest are in `triage.notJoinedFieldsByView` (below). Reconcile the headline
  as `failingFieldsByView` + `notJoinedFieldsByView`, never from one of them.
- **`warehouse.typeMismatches` is in neither.** It is reported separately and
  counted in no failing-field total, including the diff's `counts.findings`,
  which carries them as `counts.typeMismatches` instead. Adding the warehouse
  categories together to reach `failingFields` gives the right answer on some
  projects by coincidence and the wrong one on others. Don't; read `byKind`.

### What to fix, and whose fault it is

`triage.failingFieldsByView[]` is an array of `{view, count, fields[]}`. Each field
entry carries both the problem and its attribution:

```json
{ "field": "shipped_at", "declaringView": "orders",
  "file": "views/orders.view.lkml", "line": 42,
  "message": "Name shipped_at not found inside orders",
  "dashboards": [], "onIndexedDashboard": false, "inherited": false,
  "attribution": "staleReference",
  "attributionReason": "...", "dataformAction": "vw_orders",
  "dataformFile": "definitions/vw_orders.sqlx", "attributedColumn": "shipped_at",
  "attributionEvidence": "declared" }
```

`attribution` is the field that decides what kind of work an item is:

| `attribution` | What it means | The item is |
|---|---|---|
| `staleReference` | the pipeline does not produce this column and does not claim to | a LookML edit |
| `pipelineBehind` | the pipeline produces it; the table has not been rebuilt | run `dataformAction`, do not touch the LookML |
| `externalSource` | the table is not built by this Dataform project | out of this project's hands; say where it comes from |
| `outsideProject` | the reference leaves the project | not a defect to fix here |
| `unattributed` | the cross-check reached no verdict for this field | **not** a finding against the LookML — see below |
| `notCrossChecked` | no Dataform project was supplied to the run | the run was incomplete; offer to re-run with one |

### Fields whose explore doesn't join a view they read

`triage.notJoinedFieldsByView[]` has the same `{view, count, fields[]}` shape and
is the other half of `blastRadius.failingFields`:

```json
{ "field": "is_priority", "file": "views/orders_refinement.view.lkml", "line": 16,
  "referencedViews": ["segment", "account"],
  "explores": ["sales.orders", "sales.returns"], "exploresMissingTheJoin": 2,
  "dashboards": [], "onIndexedDashboard": false }
```

**One entry per field, with the explores rolled up.** The same field fails in
every explore that lacks the join, so `missingJoins` at the top level holds many
more records describing the same handful of fields — a hundred records can be a
dozen fields. Never present the record count as the number of fixes.

These are **decisions, not repairs**: each needs a join added to the explore or
the field rewritten, and which one is a modelling question for whoever owns the
model. Do not list them beside stale references as though both were typing.

`dashboards` here is scoped to the explores that lack the join. A dashboard
reading the same field through an explore that *does* join it is unaffected, so
this field can be latent while the field is charted elsewhere.

`unattributed` is the one to get right, in both directions. On a real project it is
routinely the majority — 189 of 228 in one run — and it means Graver could not
establish column provenance for that table, not that the field is wrong. Grouping
those under "fields to delete" would be the worst thing this report could do.

But a whole section called "no verdict, not actionable" is the second worst, and it
is the easier mistake to make. **Group by declaring file first, attribution second.**
In that same run, one base view accounted for 119 findings — 32 `staleReference` and
87 `unattributed` — and a report that split by attribution reported it as 32 and
filed the other 87 under "not findings". Same file, same line numbers, same defect,
73% of it hidden. A declaring site that spans attribution buckets is **one item**,
and the attributions are facts about how much of it Graver could explain, not a
partition of the work.

So: cluster on `file` (and `declaringView` for inherited fields), count the cluster,
and only then say what the attributions in it mean. A cluster that is entirely
`unattributed` and spread across one view usually resolves to a single upstream
cause too — 72 fields reading *the dry run for X was refused* is one cause, not 72
items. Report it that way, and the count becomes an argument for fixing it rather
than a reason to skip the section.

**Read `attributionReason` literally, and do not prescribe past it.** A missing
verdict has several unrelated causes and they need opposite responses:

| The reason says | What it means | What not to do |
|---|---|---|
| `the dry run for X was refused … HTTP 403` | the identity the check ran as cannot see something X reads | do not touch the LookML; re-run as an identity that can |
| `the dry run for X was refused … notRecorded` | this was a replay and the recording never covered it | re-record with `--dataform-project`; the fields are unjudged, not clean |
| `no warehouse was available` | the run had nothing to ask | the finding set is incomplete; say so |
| `X is a derived table whose SQL doesn't pass a single table through` | provenance is not derivable from the shape | genuinely no verdict |
| `not a missing-column error` | some other SQL problem | read the `message`; it may be the harness |

In particular, **never advise adding a `columns:` block to resolve one.** Graver
ignores a `columns:` block whenever the object's query is a pass-through
`select *`, because the block is a subset by construction and trusting it would
report working columns as stale. Those objects can only be judged by a dry run. A
work order that says "document this object" there is wrong twice: the block usually
already exists, and it would change nothing if it didn't.

And an `unattributed` cluster is not evidence of absence *or* of innocence. Once the
dry runs succeed, the fields get real verdicts — on the run this rule came from,
89 fields across four views that had read as "no verdict" were every one a real
stale reference, confirmed against `INFORMATION_SCHEMA` independently of the tool.

### Where the declared and the real diverge

In a sweep document, `findings[]` carries two different things per object and they
are not interchangeable:

- `phantom` — declared in `columns:`, **not produced** by the compiled query. A defect.
- `undeclared` — produced, not documented. **Not a defect**, and not nothing either:
  it is usually drift nobody noticed, and on a real project it ran to thousands of
  columns across 70 objects.
- `source` — `dryRun` means the finding is about *this commit's compiled query*;
  `tableAsLastRun` is a weaker claim, about the table as it currently stands. Carry
  the distinction; do not flatten both into "found".

### Declared type against warehouse type

`warehouse.typeMismatches[]` compares a field's declared LookML type with the type
the warehouse reports. Most mismatches are harmless. `breaksAtRunTime` is the one
that matters — only mismatches crossing a timestamp boundary actually fail a query —
so a report that lists all of them as breakage is wrong. Count and order by
`breaksAtRunTime`, and mention the rest as a tidy-up.

### What was never checked

This is the section most reports omit, and the one that decides whether a clean
result means anything.

- `referenceCoverage.fieldsChecked` / `fieldsSkippedForLiquid`
- `warehouse.skipped[]` — every skipped field by name, with `kind`:
  `liquid` (Liquid-templated SQL, never evaluated), `crossViewReference`
  (`${other_view.field}`), `noColumnOfItsOwn`. A real project skipped 107.
- `warehouse.unvalidatableViews[]` — views that could not be checked at all, with why.
- In a sweep: `complete` (a boolean, stated so coverage is never inferred from an
  absence of findings) and `notChecked[]`, every unverified candidate with its `kind`.

A view reporting "2 failing of 22" where a third field was skipped has not been
cleared. Put the coverage numbers on the same page as the findings, not in a footer.

### Provenance to put in the header

- `corpus.described` — the commit validated. `corpus.deploymentKnown` is a value, not
  an absence: `false` means Graver did not establish whether the instance serves this
  commit. When it is true, `deploymentVerdict`, `deployedCommit` and `commitsBehind`
  say what it found. A clean report about code nobody is running is still a clean
  report about code nobody is running.
- `warehouse.checkedAs` and `warehouse.identityCaveat` — which credentials answered.
  Looker reaches the warehouse as its own service account; a check run as someone
  else can pass on tables Looker cannot see.
- `warehouse.dataformIdentity.matchesWhatGraverUsed` — whether the pipeline's identity
  and the checking identity agree. When `graverIdentityKnown` is false, agreement was
  not established and must not be claimed.

## The checklist

One item per problem, not one per cause. Six parts, every time:

1. **A stable id.** Derive it; the document has no id field and does not need one.
   `view.field` keys a LookML problem (`orders.shipped_at`); `object:column` keys a
   declaration problem (`vw_orders:shipped_at`). Same id in the next run's report
   means the same problem, which is what makes two reports comparable and what lets
   `--diff` and the checklist agree.
2. **What is wrong**, in the finding's own terms.
3. **Where** — `file` and `line`. An item without them sends someone searching.
4. **The evidence**, quoted from `message`. The warehouse's own words.
   `Name X not found inside Y` is the **only** message that proves a column is absent.
   `No matching signature for operator` means something else was wrong with the SQL;
   `Syntax error: Unexpected "%"` means Liquid was never expanded and the field was
   never really checked. Do not file either as a missing column. And
   `Multi-level aggregation requires the enclosing aggregate function …` is not a
   finding at all — it means a measure whose `sql:` already aggregates was wrapped in
   another aggregate, so the error belongs to whatever built the probe. A field
   carrying it may work perfectly in production; check the tooling before writing it
   into a work order.
5. **The fix** — and which kind it is, from `attribution`. "Run `vw_orders`" and
   "remove this dimension" are different items and must not share a bullet.
6. **How to verify it moved.** Re-run and diff against this document
   (`graver-lookml --diff <this file>`), and name the id that should disappear.
   "Re-run and look" is not a verification step.

Order items by consequence: fields on an indexed dashboard, then fields on any
dashboard, then phantom declarations, then the largest declaring-site clusters, then
everything else. Skipped fields go in their own section, below, clearly not queued
for deletion — and so do the `unattributed` findings that are left *after* clustering
by declaring site, which is usually far fewer than the raw count suggests.

Attach each caveat to the items it undermines, inline. An item resting on a skipped
check, a stale replay, or an identity that was never established is not actionable,
and a footnote at the bottom of a long page does not reach the person working item 14.

## What a published report must not do

- **Do not turn "nothing reaches this" into "delete this".** Only content in git is
  visible. Dashboards and Looks built in the Looker UI are not in the repository, so
  an unused view may be charted by something Graver cannot see. The verdict is
  *defer*, and `blastRadius.caveat` says why. Some projects have a standing rule that
  everything must live in source control — that is the user's rule to state, not an
  inference to make from a clean `onNoDashboard`.
- **Do not report a fixed count from a finding count.** A finding that stopped being
  reported may have been fixed, or the field may have been deleted, or the identity
  or recording may have changed between runs. Use `--diff`, which reports what moved
  *and* the reasons the numbers may not mean what they look like.
- **Do not recommend removing a column because it is absent.** Absent **and** nothing
  upstream holds the data. A column that is gone may be one somebody wants back, and
  the sweep's own `caveat` says it infers no intent.
- **Do not repair things nobody asked about.** Report them. An agent asked to remove
  invalid columns once rewrote a working Liquid conditional because it read a column
  name as a typo.
- **Do not publish client table or column names outside the user's own workspace.**
  A findings document names real schema. Publishing to a shareable URL is a
  disclosure decision; ask before making one, and prefer a local file if unsure.

## Publishing

The content contract above is the same whichever surface you have. Use what your host
offers: an artifact or shareable page if you can publish one, a written HTML or
markdown file next to the document otherwise, or a PR comment if the audit is about a
branch. Keep the findings document itself out of the published page — it names every
table in the warehouse — and link or attach it separately.

Whatever you publish must carry, in this order: the commit and deployment state, the
replay caveats if any, the blast-radius split, the checklist, the coverage numbers,
and the identity caveat. A page that leads with a total and ends with the caveats has
inverted the document it came from.

## What a clean report does not prove

A document with zero findings means every check that ran, passed. It does not mean
the project is correct. Graver does not evaluate Liquid, does not see content built
in the Looker UI, does not know whether the instance serves the commit it validated
unless it was asked, and validates SQL by dry run — which proves a query parses and
resolves, not that it returns the right rows. The one genuine defect found on a real
project this way was a join condition that quietly reduced a view from 2,169 rows to
4: every field in it validated perfectly.

Say that on the page. A report that implies more than it checked is worse than no
report, because someone will act on it.
