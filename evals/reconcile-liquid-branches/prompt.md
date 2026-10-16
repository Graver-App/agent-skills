---
max_turns: 12
allowed_tools: [Read, Glob, Grep, Skill]
runs: 1
---

A LookML dimension in the view `words`:

```
parameter: length_floor { type: number }
filter: pick_corpus { type: string }

dimension: long_enough {
  type: yesno
  sql: {% if pick_corpus._is_filtered %}
         ${TABLE}.word_len >= {% parameter length_floor %}
         AND {% condition pick_corpus %} ${TABLE}.corpus {% endcondition %}
       {% else %}
         ${TABLE}.word_len >= 1
       {% endif %} ;;
}
```

The whole-project validator reports this field as skipped, not checked. I need to know whether
its columns are valid in the warehouse. Tell me exactly how you would check it and what you
would run. Do not ask me questions.
