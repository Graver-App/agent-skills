---
type: llm
focus: last_message
weight: 2
---

One criterion only. PASS if the answer decides whether a column is valid by **running** the
field's SQL against the warehouse — a dry run, an explore query's generated SQL, anything
executed — rather than by reading `columns:` documentation, declarations, or a naming
convention.

FAIL only if it would decide validity without running anything.
