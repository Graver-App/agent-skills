---
name: graver-looker-view-reconcile
description: Use when asked to reconcile one LookML view against its data source — "remove the columns in this view that are invalid", "check this view against the warehouse", "which dimensions here are broken". Validates every field by running its SQL as a BigQuery dry run, including the fields Graver's project-wide check skips: Liquid-templated SQL (every branch, separately), cross-view `${other_view.field}` expressions, and derived tables. Covers how to resolve Liquid and `${TABLE}` into runnable SQL, how to tell a genuinely absent column from a bad substitution, and why "invalid" never implies "delete".
license: Apache-2.0
metadata:
  source: https://graver.dev
---

# Reconciling one Looker view against its source

## What this is for

Someone points at a view and asks for the broken columns to go. The request sounds
like one step. It is three, and the middle one is the one that gets skipped:

1. **Find** the fields whose SQL the warehouse rejects.
2. **Verify** each one by running its SQL yourself — including the fields no
   project-wide check covers.
3. **Decide**, per column, whether the fix is to remove it or to restore what it
   reads. "Invalid" says the reference is wrong. It does not say which end is wrong.

Skip step 2 and you will delete a dimension because a report inherited a stale
assumption. Skip step 3 and you will delete a column whose data still exists one
join away.

> Auditing or cleaning a **whole** project — blast radius, which dashboards break
> first, proving a cleanup with a diff — is `graver-lookml-cleanup`. Come here when
> the question is about one view's columns.

Asked instead to **write up or publish** what a run found, rather than to fix a view,
use `graver-audit-report`.

## Start with the project-wide run, then distrust its coverage

`looker_validate` (MCP) or `graver-lookml` (CLI) dry-runs each field's SQL against
BigQuery and reports what it rejected. Dry runs scan no bytes, read no rows and
cost nothing, so this is safe against production.

```
looker_validate(path: "<project>", bigquery_project: "<gcp project>")
```

Filter `warehouse.rejected` to the file you were asked about. Each entry gives
`field`, `line`, `declaringView`, `inherited` and BigQuery's verbatim `message`:

```
region_code     line 84  inherited: false  declaringView: location
boundary_geom   line 51  inherited: false  declaringView: location
  message: Name boundary_geom not found inside location
```

**That list is not the answer. It is the half of the answer that was checkable.**
The validator declines to guess, which is the right call and leaves you work. On a
real 153-view project it checked 3431 fields and skipped 107. On a single real view
it reported two failing fields out of 22 — and had never looked at a third that was
broken.

Three classes get skipped, and **the report gives you counts by reason, never the
names of the fields it skipped.** You have to enumerate them yourself, from source:

| Class | How to spot it in the view | Why it was skipped |
|---|---|---|
| **Liquid** | `{%` or `{{` anywhere in a `sql:` body | Needs user attributes and filter state no static tool has |
| **Cross-view** | `${other_view.field}` in `sql:` | Only meaningful inside an explore, where the join decides what that view is called |
| **No column of its own** | `parameter:`, `filter:`, duration groups | Correct to skip — there is nothing to validate |

So: list every `dimension`, `dimension_group` and `measure` in the view, classify
each by reading its `sql:`, and hand the first two classes to the loop below.
Anything with a plain `${TABLE}.column` body is already covered by the run above.

> `html:` and `link:` parameters often carry Liquid and JavaScript too. Those render
> a cell; they never reach the warehouse, so they cannot make a column invalid.
> Ignore them here.

## Resolve the field into SQL you can actually run

Work out the view's `FROM` once, then reuse it for every field.

**The table.** `sql_table_name: \`@{proj}.@{ds}.t\`` → that table. A
`derived_table: { sql: ... }` → that SELECT, wrapped as a subquery. Expand every
`@{constant}` from `manifest.lkml` first; a leftover `@{x}` reaches BigQuery as a
syntax error that says nothing about the real cause.

```sql
-- derived_table becomes the FROM, aliased, and ${TABLE} becomes that alias
FROM (SELECT * FROM `proj.ds.location`) AS t
```

**`${TABLE}`** → the alias. **`${this_view.other_field}`** → that field's own
resolved SQL, inlined.

**`${other_view.field}`** → find the explore that joins that view, build the `FROM`
with the join from its `sql_on`, alias both sides, and inline the other field's SQL
against its alias. This is the only way the reference has a meaning:

```sql
SELECT w.total_count / NULLIF(SUM(s.total_words), 0)
FROM (SELECT * FROM `proj.ds.top_words`) AS w
LEFT JOIN `proj.ds.word_stats` AS s ON w.word = s.corpus
GROUP BY w.total_count
-- Error in query string: Name total_words not found inside s
```

If no explore joins it, the expression is unreachable as written — report that, do
not substitute a guess.

**Liquid.** Replace each construct with a literal, and **write down what you
substituted** — the verdict is only as good as the substitution, and your reader
needs to see it:

| Construct | Substitute | Why |
|---|---|---|
| `{% parameter p %}` | a literal of `p`'s declared `type` | a type mismatch here fails the query for a reason that has nothing to do with the column |
| `{% condition f %} expr {% endcondition %}` | `expr IS NOT NULL` | stays boolean whatever `expr`'s type is |
| `{% date_start f %}` / `{% date_end f %}` | a dated literal, cast as the surrounding SQL casts it | |
| `{{ _user_attributes['a'] }}` | a plausible literal value for `a` | |
| `{% assign v = ... %}` then `{{ v }}` | evaluate the assignment, substitute the result at each use | Liquid filters (`\| times:`, `\| round`) run before the SQL exists — BigQuery never sees them |
| `{% if %} / {% elsif %} / {% else %}` | **do not substitute — enumerate** | see below |

### Enumerate every branch. One dry run is not a check.

A Liquid `{% if %}` is not one SQL expression, it is several, and a column can be
missing from one branch only. A field is valid when **every reachable branch**
validates. Run them separately:

```
### weighted_rank, branch A (pick_corpus filtered)
  SELECT t.total_countx / NULLIF(t.word_len, 0) FROM ... AS t
  → Error in query string: Name total_countx not found inside t

### weighted_rank, branch B (else)
  SELECT t.total_count / NULLIF(t.word_len, 0) FROM ... AS t
  → Query successfully validated.
```

Checking branch B alone reports that field clean. It is not clean, and the failure
is invisible until someone applies the filter that selects branch A.

## Run it

Either shell out per expression:

```
bq --project_id=<proj> query --dry_run --use_legacy_sql=false '<sql>'
```

or let the warehouse half of Graver do it. Either way the identity matters: Looker
reaches BigQuery as the service account on its connection, and you are not it.
Read `warehouse.identityCaveat`. **A table you cannot see reads as missing**, so a
"not found" from credentials with narrower access is not evidence a column is gone.
If a deletion hangs on that, re-run as an identity that sees what Looker's
connection sees — a single-purpose, expiring audit account is the usual way.

## Read the error, not just the exit status

Only one of these shapes is evidence about a column. The other two mean **your
harness is wrong — fix the substitution and run it again**:

| BigQuery says | Means |
|---|---|
| `Name X not found inside Y` | **The column is absent.** This is the finding. |
| `No matching signature for operator ...` | Your `{% parameter %}` literal was the wrong type |
| `Syntax error: Unexpected "%"` | Liquid reached BigQuery — a construct you did not expand |
| `Table ... was not found` | The table, not the column — or an identity that cannot see it |
| `Multi-level aggregation requires the enclosing aggregate function ...` | **Nothing is wrong with the field.** A measure whose `sql:` already aggregates got wrapped in another aggregate. |

Counting the second and third as findings is how a reconcile turns into a round of
deletions nobody asked for.

The last row is the one that caught Graver itself out. A measure's `sql:` is the
*argument* to its aggregation, so a harness has to wrap it — and must not wrap one
that already aggregates. Looker's non-aggregate measure types carry their own
aggregate: `number`, `string`, `yesno`, `date`, the untyped measure (which defaults
to `string`), and `date_time`, which is not in Looker's documented list at all even
though projects write it. Wrap those and you manufacture this error against a field
that works in production. If you see it, check your own wrapper before you believe
it.

## Then decide, per column — and do not default to delete

A dry run tells you the reference is wrong. It cannot tell you which end to fix.
Before removing anything, answer these from git and the warehouse:

1. **When did it stop resolving?** `git log -S'<column>'` on the source model. A
   column that was dropped on a dated commit is a decision; a column that was never
   there is a typo. They have different fixes.
2. **Does the data still exist anywhere?** A column can leave an optimized or
   rebuilt table and still sit in the upstream source it was derived from. Then the
   honest fix is to restore the join, not to delete the dimension.
3. **Who is using it?** Only what is in git is visible. Dashboards and Looks built
   in the Looker UI are not in the repository, so "no dashboard charts this" means
   **defer**, never **delete** — and say what you deferred.

A failing dimension is not an unused one. It is already erroring for whoever
queries it, which is an argument for fixing it, not for assuming nobody cared.

**The dividing line is whether the data still exists.**

- **Absent from the source and held nowhere upstream** — there is nothing to
  restore, so a blanket "remove the invalid columns" covers it. Remove it, and say
  you checked for an upstream copy and found none.
- **The column exists somewhere** — in the upstream table, under a different name,
  one join away — then the reference is the wrong end, not the column. Removing the
  field deletes something that works or could work. **Stop and present the choice**
  with its evidence: "dropped in `<sha>` on `<date>`, still present upstream in
  `<table>`: restore the join, or remove the dimension?"

A one-character difference from a real column (`total_countx` next to
`total_count`) is the second case, not the first.

### Repair only what you were asked to repair

A field can be broken in one branch and correct in another. Fixing the broken
branch is a different job from removing an invalid column, and it is not yours
unless it was asked for. Do not rewrite a field's structure in passing — do not
collapse a Liquid conditional because its branches became identical after you
"fixed" one, do not rename a column you decided was a typo, do not touch a second
view because the broken end turned out to live there. Name the one-line fix in your
report and leave it for the human.

That restraint is the whole difference between a reconcile and an unreviewed
refactor, and the diff is where it shows: one deletion you can read in ten seconds,
or a structural edit nobody asked for buried next to it.

## Prove the edit

Save the first run's JSON **outside the project** (a findings document names client
tables), then re-run with `diff_from` and report what moved. Watch
`referenceCoverage.fieldsChecked` alongside the failure count: if both drop,
fields were removed rather than fixed. That may be exactly what was asked for. It
is not the same thing, and the diff will not say "fixed" for you.

## Don't

- **Don't conclude anything from a `columns:` block.** Documentation drifts from
  what a query selects; a declared column that was never produced is how a column
  that left the warehouse a year ago still looks real.
- **Don't report a Liquid field as valid off one branch.**
- **Don't treat a skipped check as a passed check.** The project-wide markdown work
  order (`--triage`) does not restate its own coverage — read the plain report, or
  the JSON's `referenceCoverage` and `warehouse.unvalidatableViews`, to see what was
  never looked at.
- **Don't delete on "nothing reaches it".** See the git caveat above.
- **Don't paste a verdict without the substitutions.** "Valid" under unstated
  parameter values is not a result anyone can check.
- **Don't let the edit grow past the verdicts.** Every change in the diff should
  trace to a column you proved absent. If it doesn't, it belongs in the report as a
  suggestion, not in the file.
