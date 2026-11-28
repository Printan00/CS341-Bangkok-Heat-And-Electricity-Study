-- Q3 key SQL for the presentation slide
-- Source: happy_home_risk. Thresholds follow the project rule at 0.5.
WITH classified AS (
    SELECT CASE
               WHEN exposure < 0.5 THEN 'lower_exposure'
               WHEN vulnerability >= 0.5 THEN 'help_first'
               ELSE 'watch'
           END AS priority_group,
           risk_score, exposure, vulnerability,
           heat_risk, housing_risk, finance_risk, burden_risk, coping_risk
    FROM happy_home_risk
    WHERE exposure BETWEEN 0 AND 1
      AND vulnerability BETWEEN 0 AND 1
), grouped AS (
    SELECT priority_group,
           count(*) AS households,
           IF(count(risk_score) >= 5, round(avg(risk_score), 1), NULL) AS risk_score,
           round(100 * avg(exposure), 1) AS exposure,
           round(100 * avg(vulnerability), 1) AS vulnerability,
           IF(count(heat_risk) >= 5, round(100 * avg(heat_risk), 1), NULL) AS heat,
           IF(count(housing_risk) >= 5, round(100 * avg(housing_risk), 1), NULL) AS housing,
           IF(count(finance_risk) >= 5, round(100 * avg(finance_risk), 1), NULL) AS finance,
           IF(count(burden_risk) >= 5, round(100 * avg(burden_risk), 1), NULL) AS burden,
           IF(count(coping_risk) >= 5, round(100 * avg(coping_risk), 1), NULL) AS coping
    FROM classified
    GROUP BY priority_group
), disclosure AS (
    -- If any group is smaller than five, suppress every group total.
    SELECT *, min(households) OVER () < 5 AS suppressed
    FROM grouped
)
SELECT priority_group,
       suppressed,
       IF(suppressed, NULL, households) AS households,
       IF(suppressed, NULL, risk_score) AS risk_score,
       IF(suppressed, NULL, exposure) AS exposure,
       IF(suppressed, NULL, vulnerability) AS vulnerability,
       IF(suppressed, NULL, heat) AS heat,
       IF(suppressed, NULL, housing) AS housing,
       IF(suppressed, NULL, finance) AS finance,
       IF(suppressed, NULL, burden) AS burden,
       IF(suppressed, NULL, coping) AS coping
FROM disclosure
ORDER BY CASE priority_group
             WHEN 'help_first' THEN 1
             WHEN 'watch' THEN 2
             ELSE 3
         END;
