# Contributing / maintaining this repo

This repo is the **single canonical source** of the public Graver skills. It is public so
that an agent can learn what Graver does before anyone installs it; Graver itself is a
private repo and nothing here may depend on a reader having it.

## Keep it self-contained

- No references to private repos, personal skill ecosystems, internal paths, or any
  client's project. The skills describe Graver's own surface and nothing else.
- Project-specific facts (a particular warehouse's conventions, placeholder declarations
  that must not be deleted, a team's suffix rules) belong in a per-project skill the user
  owns — not here.

## Release sync (mandatory)

Graver's MCP tool surface is the contract these skills document, so on every Graver
release check the skills against it in the same pass:

1. Dump the live surface rather than reading the Swift — it is what an agent actually
   sees. With Graver running, `tools/list` against its HTTP MCP endpoint lists every tool
   with its arguments.
2. For each tool these skills name, confirm the name, the argument names, and anything the
   skill claims about behaviour. **Arguments are the part that rots**: `looker_validate`
   gained `index`, then `triage`, `looker_url` and `diff_from` across three releases.
3. Re-check the refusal rules. `graver-dataform-workbench` states exactly which action
   types a native run refuses; that set has already changed once (incrementals using
   `MERGE` with `onSchemaChange: IGNORE` became supported, so "incrementals need the
   terminal" became wrong).
4. Keep the frontmatter `description` stable unless the trigger surface genuinely changed
   — it is what agents match on.

## Test before merging (mandatory for a skill change)

This repo is also a Claude Code plugin (`.claude-plugin/plugin.json`, name
`graver-skills`), which is what lets the eval harness load the skills and run a
no-plugin baseline arm beside them:

```bash
claude plugin eval . --runs 1 --no-publish --trust-plugin -j 2
```

Each case is `evals/<case>/prompt.md` plus `evals/<case>/graders/*.md`. Results land in
`evals/results/` (gitignored); the numbers worth keeping go in `evals/BASELINE.md` by
hand, with the date and the run count.

**When you add a rule a skill must teach, add a case that fails without it** — and then
check the Δ, because a case that scores the same on both arms measures nothing. Two of
the first four did exactly that; `BASELINE.md` says which and why, and carries the
grader-authoring traps worth reading before writing one (vacuous `not_contains`
graders, JavaScript regex flags, column-0 frontmatter, and how a wrong `input_match`
reads exactly like a skill that never fired).

Anthropic's official `skill-creator` plugin
(`/plugin install skill-creator@claude-plugins-official`) covers the authoring side of
this loop and adds something this suite does not have: `scripts/improve_description.py`
and `scripts/run_loop.py` optimise a skill's `description` for **triggering** accuracy,
with a train/test split. Worth reaching for when a skill is not firing on the requests
it was written for — `trigger-user-phrasing` detects that, but does not fix it.

Evals cost money and need model access, so they are a local gate rather than CI. CI
lints frontmatter only.

## Conventions

- One directory per skill under `skills/`, each with a `SKILL.md` whose frontmatter `name`
  matches the directory, per the [Agent Skills spec](https://agentskills.io).
- CI lints frontmatter on every push and PR (`.github/workflows/lint.yml`).
- Claims must be verifiable. Prefer a measured number to an adjective, and state what a
  tool cannot tell you next to what it can — an agent that trusts a number too far does
  more damage than one that asks.
