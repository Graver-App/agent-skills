---
type: tool_used
tool: Skill
input_match: '"skill"\s*:\s*"(?:[\w-]+:)?graver-looker-view-reconcile"'
min: 1
---

This is the triggering test, and the indicator is the point of the case rather than a
side-check: the prompt is a user's own unprompted words, naming neither Graver nor any
tool. If the skill does not fire here, its `description` is not reaching the request it
was written for — and every other case in this suite, which names the validator
explicitly, would still pass while the skill went unused in practice.
