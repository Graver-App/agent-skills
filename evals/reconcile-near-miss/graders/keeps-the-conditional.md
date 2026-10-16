---
type: regex
pattern: '(leav(e|ing)|keep(ing)?|retain(ing)?|do(es)? not (remove|delete)|without (removing|deleting))'
flags: 'i'
match: contains
target: last_message
weight: 1
---

The answer must positively state that the dimension stays. Written as a positive pattern on
purpose: a `not_contains` assertion that the answer avoids some wrong phrase is satisfied by an
answer that says nothing relevant at all, which hands the no-skill arm free credit. The rubric
carries the case; this is its deterministic companion.
