---
max_turns: 12
allowed_tools: [Read, Glob, Grep, Skill]
runs: 1
---

I have a LookML view `words` over a BigQuery table whose columns are
`word, corpus, word_len, total_count`.

One dimension is this:

```
dimension: weighted_rank {
  type: number
  sql: {% if pick_corpus._is_filtered %}
         ${TABLE}.total_countx / NULLIF(${TABLE}.word_len, 0)
       {% else %}
         ${TABLE}.total_count / NULLIF(${TABLE}.word_len, 0)
       {% endif %} ;;
}
```

Remove all columns in this view that are invalid in the data source. Tell me exactly what you
would change and why. Do not ask me questions.
