WITH survey AS (
  SELECT CASE income_group
           WHEN '1) ไม่เกิน 10,000' THEN 'lower'
           WHEN '2) 10,001-20,000' THEN 'middle'
           WHEN '3) มากกว่า 20,000' THEN 'upper'
           ELSE 'unknown'
         END AS income,
         CASE has_aircon WHEN true THEN 'yes' WHEN false THEN 'no' ELSE 'unknown' END AS cooling,
         burden_class
  FROM happy_home_risk
), totals AS (
  SELECT CASE WHEN grouping(income) = 1 THEN 'cooling'
              WHEN grouping(cooling) = 1 THEN 'income' ELSE 'combined' END AS breakdown,
         coalesce(income, 'all') AS income, coalesce(cooling, 'all') AS cooling,
         count(*) AS households,
         count_if(burden_class = 'high') AS high,
         count_if(burden_class = 'possibly_high') AS possibly_high,
         count_if(burden_class = 'low') AS low,
         count_if(burden_class IS NULL OR burden_class NOT IN ('high', 'possibly_high', 'low')) AS missing
  FROM survey
  GROUP BY GROUPING SETS ((income), (cooling), (income, cooling))
), disclosure AS (
  SELECT *,
         bool_or(households < 5) OVER (PARTITION BY breakdown = 'combined') AS hide_size,
         bool_or(high BETWEEN 1 AND 4 OR possibly_high BETWEEN 1 AND 4
                 OR low BETWEEN 1 AND 4 OR missing BETWEEN 1 AND 4)
           OVER (PARTITION BY breakdown = 'combined') AS hide_burden
  FROM totals
)
-- Mask linked distributions together: releasing complementary cells or marginal
-- totals from the same breakdown can expose a small count by subtraction.
SELECT breakdown, income, cooling,
       IF(hide_size, NULL, households) AS households,
       IF(hide_size OR hide_burden, NULL, high) AS high,
       IF(hide_size OR hide_burden, NULL, possibly_high) AS possibly_high,
       IF(hide_size OR hide_burden, NULL, low) AS low,
       IF(hide_size OR hide_burden, NULL, missing) AS missing
FROM disclosure
ORDER BY breakdown, income, cooling
