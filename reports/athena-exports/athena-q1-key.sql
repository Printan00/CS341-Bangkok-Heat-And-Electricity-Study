-- Q1 key SQL for the presentation slide
-- Source: happy_home_household, filtered by usable_q1
-- Query 1: compare the high heat-impact rate for wood vs other wall materials.
WITH base AS (
    SELECT
        IF(b3_wall_material_clean = 'ไม้', 'wood', 'other') AS wall,
        heat_impact_level
    FROM happy_home_household
    WHERE usable_q1
      AND heat_impact_level IN ('low', 'medium', 'high')
      AND heat_impact_score BETWEEN 0 AND 13
), grouped AS (
    SELECT wall,
           count(*) AS households,
           count_if(heat_impact_level = 'high') AS high
    FROM base
    GROUP BY wall
), disclosure AS (
    SELECT *,
           max(IF(households < 5
                  OR high BETWEEN 1 AND 4
                  OR households - high BETWEEN 1 AND 4, 1, 0)) OVER () = 1
               AS suppressed
    FROM grouped
)
SELECT wall,
       IF(suppressed, NULL, households) AS households,
       IF(suppressed, NULL, high) AS high,
       IF(suppressed, NULL, round(100.0 * high / households, 1)) AS high_pct,
       suppressed
FROM disclosure
ORDER BY wall;

-- Query 2: heatmap cells, with one shared suppression rule for the full grid.
WITH base AS (
    SELECT
        CASE b8_ventilation_clean
            WHEN 'ดี' THEN 'good'
            WHEN 'ปานกลาง' THEN 'moderate'
            WHEN 'ไม่ดี' THEN 'poor'
            ELSE 'unknown'
        END AS airflow,
        IF(b3_wall_material_clean = 'ไม้', 'wood', 'other') AS wall,
        heat_impact_score
    FROM happy_home_household
    WHERE usable_q1
      AND heat_impact_level IN ('low', 'medium', 'high')
      AND heat_impact_score BETWEEN 0 AND 13
), cells AS (
    SELECT airflow,
           wall,
           count(*) AS households,
           round(avg(heat_impact_score), 2) AS avg_impact
    FROM base
    GROUP BY airflow, wall
), disclosure AS (
    SELECT *, max(IF(households < 5, 1, 0)) OVER () = 1 AS suppressed
    FROM cells
)
SELECT airflow,
       wall,
       IF(suppressed, NULL, households) AS households,
       IF(suppressed, NULL, avg_impact) AS avg_impact,
       suppressed
FROM disclosure
ORDER BY airflow, wall;
