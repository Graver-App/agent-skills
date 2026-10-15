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

## Conventions

- One directory per skill under `skills/`, each with a `SKILL.md` whose frontmatter `name`
  matches the directory, per the [Agent Skills spec](https://agentskills.io).
- CI lints frontmatter on every push and PR (`.github/workflows/lint.yml`).
- Claims must be verifiable. Prefer a measured number to an adjective, and state what a
  tool cannot tell you next to what it can — an agent that trusts a number too far does
  more damage than one that asks.
