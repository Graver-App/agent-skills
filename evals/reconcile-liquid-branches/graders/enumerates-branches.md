---
type: llm
focus: last_message
weight: 3
---

PASS only if the answer checks **both** branches of the `{% if %}` separately — one dry run per
branch, not a single query — and says why: a column can be absent from one branch only, so one
dry run would report the field clean.

It must also state the substitutions it makes rather than leaving them implicit: a literal of the
declared type for `{% parameter length_floor %}` (it is `type: number`, so a number), and a
predicate that stays boolean for `{% condition pick_corpus %} ... {% endcondition %}`.

FAIL if it checks only one expression, if it leaves any `{%` construct in the SQL it proposes to
run, or if it never says which values it substituted.
