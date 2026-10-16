---
type: regex
pattern: 'dry.?run'
flags: 'i'
match: contains
target: last_message
weight: 1
---

The check must be a dry run. A dry run scans no bytes and reads no rows, which is what makes
this safe to do against a production warehouse.
