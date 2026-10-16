---
max_turns: 14
allowed_tools: [Read, Glob, Grep, Skill]
runs: 2
---

Remove all columns in this looker view that are invalid in the Data source.

```
view: location {
  derived_table: {
    sql: SELECT * FROM `@{bq_project}.@{bq_dataset}.looker_location` ;;
  }

  dimension: zip { type: zipcode  sql: ${TABLE}.zip ;; }
  dimension: boundary_geom { type: string  sql: ${TABLE}.boundary_geom ;; }
  dimension: region_code { type: string  sql: ${TABLE}.region_code ;; }

  parameter: distance_radius { type: number }
  filter: select_zip_radius { type: string }

  dimension: within_radius {
    type: yesno
    sql: {% if select_zip_radius._is_filtered %}
           ST_DISTANCE(
             ${TABLE}.internal_point_geom,
             (SELECT internal_point_geom
                FROM `@{bq_project}.@{bq_dataset}.looker_location`
               WHERE {% condition select_zip_radius %} zip {% endcondition %}
               LIMIT 1)
           ) / 1609.34 <= {% parameter distance_radius %}
         {% else %}
           FALSE
         {% endif %} ;;
  }
}
```

Some of these dimensions are complicated SQL with embedded variables that resolve via Looker.
Do not ask me questions — tell me how you would go about it and what you would check.
