---
type: llm
focus: last_message
weight: 2
---

One criterion only. The `within_radius` dimension's SQL has two Liquid branches: the filtered
branch computes `ST_DISTANCE(...)`, the `{% else %}` branch is `FALSE`.

PASS if the answer checks the branches **separately**, or otherwise makes clear that checking
only one of them would miss a break — for example by noting that the `else` branch always
passes and so proves nothing about the other.

FAIL if it treats the dimension as a single expression to check once.
