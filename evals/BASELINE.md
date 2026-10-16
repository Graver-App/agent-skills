# Eval baseline

Recorded **2026-10-15**, the first suite for this repo. Model: the CLI default;
judge: `haiku` (the default).

These are the **last observed** values, not a pass mark. `--threshold` gates on the
**with** score; Δ is diagnostic — it says whether the skill is why the answer was good.

```
claude plugin eval . --runs 1 --no-publish --trust-plugin -j 2
```

| Case | with | w/out | Δ | Runs | Notes |
|---|---|---|---|---|---|
| `reconcile-near-miss` | 1.00 | 0.25 | **+0.75** | 2 | Discriminating. The unaided arm deletes the dimension (`does-not-delete`: FAIL FAIL FAIL) even though `total_count` exists beside the bad `total_countx`. This is the exact behaviour an unskilled agent showed in the RED/GREEN run that led to the skill: it "fixed" the typo, then collapsed the Liquid conditional because the branches had become identical. |
| `reconcile-liquid-branches` | 1.00 | 0.25 | **+0.75** | 2 | Discriminating. The unaided arm does not enumerate the `{% if %}` branches separately and does not state its substitutions (`enumerates-branches`: FAIL FAIL FAIL). It does say "dry run" unaided, so that grader is a companion, not the discriminator. |
| `trigger-user-phrasing` | 0.75 | 0.50 | +0.25 | 4 | **VOLATILE** — judge noise visible (`dry-runs-the-sql` went FAIL FAIL PASS in one with-run on an answer that plainly dry-runs). The score is secondary here: this case exists for its `skill-fired` indicator, and **the skill fires on a user's own unprompted words, naming neither Graver nor any tool.** Every other case names the validator, so without this one a description that never triggered in practice would still show a healthy suite. |
| `cleanup-gone-is-not-fixed` | 0.88 | 1.00 | −0.13 | 4 | **Not discriminating.** The unaided arm declines to call the findings fixed in every run. The negative Δ is the `states-the-weaker-claim` regex missing the skilled arm's phrasing, not a skill regression. Regression guard only. |
| `cleanup-defer-not-delete` | 1.00 | 1.00 | 0.00 | 4 | **Not discriminating.** Baseline Claude reliably refuses to delete on "nothing reaches it" and names Looker-UI content as the blind spot unaided. The skill fires and agrees. Regression guard only. |

## What the first suite taught

**Two of five cases measure nothing**, and both are `graver-lookml-cleanup` rules that
turn out to be things the model already does: default caution covers "don't delete what
looks unused" and "don't call a disappeared finding fixed". That does not make the rules
wrong — they are load-bearing when an agent is under pressure to show a cleanup worked —
but they are not what the skill is *for*, and a suite of cases like them would report a
healthy mean Δ while proving nothing.

The material that discriminates is narrower than expected, and it is not detection.
Both arms find the broken column. Only the skilled arm declines to delete a reference
that nearly matches a real column, and only the skilled arm checks every branch of a
conditional while stating the substitutions it made.

## Two grader bugs, both of which read as skill failures

**A wrong `input_match` looks exactly like a plugin that never loaded.** Every
`skill-fired` grader reported `Skill called 0x` in both arms on the first attempt. The
plugin was loading and the skill was firing. Plugin skills are namespaced by **plugin
name**, so the Skill input is `{"skill": "graver-skills:graver-lookml-cleanup"}` — not
the GitHub org, which is what the pattern had guessed. While that was wrong the with arm
was noise and one case reported Δ **−0.75**. Trust a negative Δ only after the
skill-fired indicator is green.

**A compound rubric fails correct answers.** `trigger-user-phrasing` first used one
grader demanding two criteria plus two FAIL clauses. It voted FAIL FAIL FAIL on a with-arm
answer that enumerated both Liquid branches, stated every substitution, triaged the three
BigQuery error shapes, checked upstream before deleting, and kept the edit small — i.e.
an answer that did everything the skill teaches. Split into two graders of one criterion
each, the same case went to Δ +0.25. **One criterion per grader.**

## Writing a case

- **Test what the skill teaches, not what the model knows.** Check Δ before believing a
  case. A case scoring 1.00 on both arms is a regression guard at best.
- **One criterion per grader**, and keep FAIL clauses to the inverse of the PASS
  criterion. Put a second requirement in a second grader.
- **A `not_contains` grader passes vacuously.** It cannot tell "did the right thing" from
  "said nothing relevant", so it hands the without arm free credit. Encode absence as a
  **positive** pattern: require the answer to state the thing.
- **Give the case something concrete.** A prompt naming a file that does not exist in the
  eval workspace makes both arms answer in the abstract and the scores wander. Inline the
  LookML.
- **Do not make a prompt easier to trigger in order to fix a firing problem.** One prompt
  here was edited to name `looker_validate` explicitly for exactly that reason — and the
  firing problem was the grader bug above. The edit has been reverted; `trigger-user-phrasing`
  now covers triggering properly.
- Grader frontmatter must start at column 0 or the grader is silently ignored.
- Regex graders run in JavaScript: an inline `(?i)` throws and scores **both** arms 0.
  Case-insensitivity goes in a separate `flags: 'i'` field.
- A single run is noisy. Mark a case VOLATILE rather than quoting one run as the number.
- To see what happened: `--json <file>` carries each run's `graders[].evidence` (the
  answer the judge saw) and `judgeVotes`. `--keep-temp --verbose` additionally leaves a
  `trace.jsonl` whose `system/init` line lists the tools and whose `tool_use` lines show
  each Skill call's real input. `claude plugin details` only accepts installed plugin
  names, so for a path-loaded plugin the JSON and the trace are the way in.

Cost: about **$0.14 per case per arm-pair** at `--runs 1`; the five-case suite runs in
roughly 80s at `-j 2`.
