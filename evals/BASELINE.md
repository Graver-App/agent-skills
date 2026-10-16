# Eval baseline

Recorded **2026-10-15**, the first suite for this repo. Model: the CLI default;
judge: `haiku` (the default). Run with `--runs 1` unless the row says otherwise.

These are the **last observed** values, not a pass mark. `--threshold` gates on the
**with** score; Δ is diagnostic — it says whether the skill is why the answer was good.

```
claude plugin eval . --runs 1 --no-publish --trust-plugin -j 2
```

| Case | with | w/out | Δ | Runs | Notes |
|---|---|---|---|---|---|
| `reconcile-near-miss` | 1.00 | 0.25 | **+0.75** | 2 | Discriminating. The unaided arm deletes the dimension (`does-not-delete`: FAIL FAIL FAIL) even though `total_count` exists next to the bad `total_countx`. This is the exact behaviour an unskilled agent showed in the RED/GREEN run that led to the skill: it "fixed" the typo and then collapsed the Liquid conditional because the branches had become identical. |
| `reconcile-liquid-branches` | 1.00 | 0.25 | **+0.75** | 2 | Discriminating. The unaided arm does not enumerate the `{% if %}` branches separately and does not state its substitutions (`enumerates-branches`: FAIL FAIL FAIL). It does say "dry run" unaided, so that grader is a companion, not the discriminator. |
| `cleanup-gone-is-not-fixed` | 1.00 | 0.88 | +0.13 | 4 | **Barely discriminating.** The unaided arm passes the rubric in every run — it declines to call the findings fixed on its own — and only sometimes misses the phrasing the regex wants. Keep as a regression guard; do not cite it as evidence the skill works. |
| `cleanup-defer-not-delete` | 1.00 | 1.00 | 0.00 | 4 | **Not discriminating.** Baseline Claude reliably refuses to delete on "nothing reaches it" and names Looker-UI content as the blind spot unaided. The skill fires and agrees. Kept as a regression guard only. |

## What the first run taught

**Two of four cases measure nothing.** Both are rules from `graver-lookml-cleanup`, and
both are things the model already does: default caution covers "don't delete what looks
unused" and "don't call a disappeared finding fixed". That does not make the rules wrong
— they are load-bearing when an agent is under pressure to show a cleanup worked — but
they are not what the skill is *for*, and a suite of cases like them would report a
healthy mean Δ while proving nothing.

The material that does discriminate is narrower than expected: not detection, but
**decisions**. Whether to delete a reference that nearly matches a real column, and
whether to check every branch of a conditional rather than one. Both arms find the
broken column; only the skilled arm handles it correctly.

**A grader bug reads exactly like a skill failure.** Every `skill-fired` grader reported
`Skill called 0x` in both arms on the first attempt, which looks like the plugin not
loading. The plugin was loading and the skill was firing; `input_match` was wrong.
Plugin skills are namespaced by **plugin name**, so the Skill input is
`{"skill": "graver-skills:graver-lookml-cleanup"}` — not the GitHub org, which is what
the pattern had guessed. Until that was fixed the with arm's scores were noise, and one
of them read Δ **-0.75**. Trust a negative Δ only after confirming the skill fired.

## Writing a case

- **Test what the skill teaches, not what the model knows.** Check Δ before believing a
  case. A case that scores 1.00 on both arms is a regression guard at best.
- **A `not_contains` grader passes vacuously.** It cannot tell "did the right thing" from
  "said nothing relevant", so it hands the without arm free credit. Encode the absence as
  a **positive** pattern: require the answer to state the thing.
- Grader frontmatter must start at column 0 or the grader is silently ignored.
- Regex graders run in JavaScript: an inline `(?i)` throws and scores **both** arms 0.
  Case-insensitivity goes in a separate `flags: 'i'` field.
- A single run is noisy. `cleanup-gone-is-not-fixed` showed 1.00/0.75 and 1.00/1.00 on
  consecutive runs; the rubric passed every time and the regex did not.
- To see what actually happened: `--keep-temp --verbose --json <file>` leaves a
  `trace.jsonl` whose `system/init` line lists the tools and whose `tool_use` lines show
  each Skill call's real input. `claude plugin details` only accepts installed plugin
  names, so the trace is the way to inspect a path-loaded plugin.

Cost for the full four-case suite at `--runs 1`: about **$0.55** and 82s at `-j 2`.
