-- Q2 key SQL for the presentation slide
-- Source: bhes.happy_home_risk. "high" uses the survey's 10% burden threshold.
WITH grouped AS (
    SELECT IF(grouping(income_group) = 0, 'income', 'cooling') AS breakdown,
           CASE
               WHEN grouping(income_group) = 0 THEN coalesce(income_group, 'ไม่ระบุรายได้')
               WHEN has_aircon THEN 'มีแอร์'
               WHEN has_aircon = FALSE THEN 'ไม่มีแอร์'
               ELSE 'ไม่ระบุการมีแอร์'
           END AS survey_group,
           count(*) AS households,
           count_if(burden_class = 'high') AS high,
           count_if(burden_class = 'possibly_high') AS possibly_high,
           count_if(burden_class = 'low') AS low,
           count_if(burden_class IS NULL OR burden_class NOT IN ('high', 'possibly_high', 'low')) AS missing
    FROM bhes.happy_home_risk
    GROUP BY GROUPING SETS ((income_group), (has_aircon))
), disclosure AS (
    SELECT *,
           bool_or(households < 5) OVER () AS hide_size,
           bool_or(high BETWEEN 1 AND 4 OR possibly_high BETWEEN 1 AND 4
                   OR low BETWEEN 1 AND 4 OR missing BETWEEN 1 AND 4) OVER () AS hide_burden
    FROM grouped
)
SELECT breakdown, survey_group,
       IF(hide_size, NULL, households) AS households,
       IF(hide_size OR hide_burden, NULL, high) AS high,
       IF(hide_size OR hide_burden, NULL, round(100.0 * high / households, 1)) AS pct_high
FROM disclosure
ORDER BY CASE breakdown WHEN 'income' THEN 1 ELSE 2 END, survey_group
