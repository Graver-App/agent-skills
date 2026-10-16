---
type: regex
pattern: 'no longer reported|not (necessarily )?(the same as |mean(s)? )?fixed|does not (mean|prove|say) (they were |it was )?fixed'
flags: 'i'
match: contains
target: last_message
weight: 1
---

The answer must use the weaker, true claim rather than "fixed". Positive pattern: it has to say
the thing, not merely avoid the wrong word.
