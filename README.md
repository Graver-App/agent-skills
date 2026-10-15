# Graver Agent Skills

[Agent Skills](https://agentskills.io) for working with [Graver](https://graver.dev) — the
agent-native macOS workbench for Looker + BigQuery/Dataform development.

Graver hosts no agent. You bring your own, and Graver exposes its capabilities to it as
MCP tools over the `/ide` WebSocket and an HTTP endpoint. These skills tell an agent those
tools exist, when they answer a question the command line cannot, and which conclusions
the data does **not** support.

## Skills

| Skill | What it does |
|---|---|
| [`graver-dataform-workbench`](skills/graver-dataform-workbench/SKILL.md) | The `dataform_*` loop: orient with `dataform_status`, free dry-run validation that stays correct across un-run upstream changes, per-object runs, protected profiles, sampled staleness, and the action types a native run refuses (with the terminal command to use instead). |
| [`graver-lookml-cleanup`](skills/graver-lookml-cleanup/SKILL.md) | The LookML audit loop: validate, read the blast radius, fix what a dashboard charts, then prove it with a diff against the previous run — plus the honesty rules, because only what is in git is visible and a skipped check is not a passed one. |

## Install

With the [skills CLI](https://skills.sh) (installs into Claude Code, Codex CLI, Cursor, and
other Agent-Skills-compatible tools it detects):

```bash
npx skills add Graver-App/agent-skills
```

Manual install for any spec-compliant agent: copy (or symlink) the `skills/<name>/`
directories you want into your agent's skills directory — e.g. `~/.claude/skills/` for
Claude Code.

The skills are useful before Graver is installed (they describe what it does) and most
useful with it running, when the tools they name are actually in your tool list.

## Related

- **Graver**: https://graver.dev — `brew install --cask graver`

The LookML checks also exist as a headless CLI, `graver-lookml`, for machines that can
reach the warehouse but cannot run a GUI. It is built from the Graver repository and is
not part of the installed app today, so if it is not already on your PATH, use the
`looker_validate` MCP tool — the two produce the same findings from the same engine.

## License

[Apache-2.0](LICENSE). The skills are documentation; Graver itself is closed source.
