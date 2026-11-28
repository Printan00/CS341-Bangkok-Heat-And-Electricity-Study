WITH base AS (
  SELECT b1_housing_type_clean, b3_wall_material_clean, b4_roof_material_clean,
         b6_ceiling_clean, b7_insulation_clean, b8_ventilation_clean, b9_shade_clean,
         community_key, coping_limited, housing_heat_score, heat_impact_level, heat_impact_score
  FROM happy_home_household
  WHERE usable_q1
    AND heat_impact_level IN ('low', 'medium', 'high')
    AND heat_impact_score BETWEEN 0 AND 13
), features AS (
  SELECT 'comparison' AS kind, feature AS dimension, category AS label,
         count(*) AS households, count_if(heat_impact_level = 'high') AS high,
         round(100.0 * count_if(heat_impact_level = 'high') / count(*), 1) AS value
  FROM base
  CROSS JOIN UNNEST(
    ARRAY['wall', 'ventilation', 'roof', 'ceiling'],
    ARRAY[
      IF(b3_wall_material_clean = 'ไม้', 'wood', 'other'),
      IF(b8_ventilation_clean = 'ไม่ดี', 'poor', 'other'),
      IF(b4_roof_material_clean = 'สังกะสี/เมทัลชีท', 'metal', 'other'),
      IF(b6_ceiling_clean = 'ไม่มี', 'absent', 'other')
    ]
  ) AS compared(feature, category)
  GROUP BY feature, category
), feature_detail AS (
  -- Publish averages for the finer categories without deriving their exact
  -- high-impact counts from the binary comparisons.
  SELECT 'feature_detail' AS kind, feature AS dimension, category AS label,
         count(*) AS households, CAST(NULL AS bigint) AS high, round(avg(heat_impact_score), 2) AS value
  FROM base
  CROSS JOIN UNNEST(
    ARRAY['housing_type', 'wall', 'roof', 'ceiling', 'insulation', 'ventilation', 'shade'],
    ARRAY[
      CASE b1_housing_type_clean WHEN 'บ้านเดี่ยว' THEN 'single'
           WHEN 'บ้านแถว/ทาวน์เฮาส์' THEN 'rowhouse' ELSE 'other' END,
      CASE b3_wall_material_clean WHEN 'ไม้' THEN 'wood'
           WHEN 'คอนกรีต' THEN 'concrete' ELSE 'other' END,
      IF(b4_roof_material_clean = 'สังกะสี/เมทัลชีท', 'metal', 'other'),
      IF(b6_ceiling_clean = 'ไม่มี', 'absent', 'other'),
      IF(b7_insulation_clean = 'ไม่มี', 'absent', 'other'),
      CASE b8_ventilation_clean WHEN 'ดี' THEN 'good' WHEN 'ปานกลาง' THEN 'moderate'
           WHEN 'ไม่ดี' THEN 'poor' ELSE 'unknown' END,
      CASE b9_shade_clean WHEN 'ไม่มีเลย' THEN 'none' WHEN 'น้อย' THEN 'little'
           WHEN 'พอมี' THEN 'moderate' WHEN 'มาก' THEN 'substantial' ELSE 'unknown' END
    ]
  ) AS compared(feature, category)
  GROUP BY feature, category
), community AS (
  SELECT 'community' AS kind, 'community' AS dimension,
         IF(community_key IN ('คนรักถิ่น', 'หลังแฟลต'), community_key, 'unknown') AS label,
         count(*) AS households, CAST(NULL AS bigint) AS high, round(avg(heat_impact_score), 2) AS value
  FROM base GROUP BY 3
), context AS (
  SELECT 'profile' AS kind, feature AS dimension, category AS label,
         count(*) AS households, count_if(heat_impact_level = 'high') AS high,
         round(100.0 * count_if(heat_impact_level = 'high') / count(*), 1) AS value,
         count_if(heat_impact_level = 'low') AS low, count_if(heat_impact_level = 'medium') AS medium
  FROM base
  CROSS JOIN UNNEST(
    ARRAY['coping', 'housing_risk'],
    ARRAY[
      CASE coping_limited WHEN true THEN 'limited' WHEN false THEN 'not_limited' ELSE 'unknown' END,
      CASE WHEN housing_heat_score BETWEEN 0 AND 2 THEN '0-2'
           WHEN housing_heat_score BETWEEN 3 AND 5 THEN '3-5' ELSE 'unknown' END
    ]
  ) AS grouped(feature, category)
  GROUP BY feature, category
), grid AS (
  SELECT CASE b8_ventilation_clean WHEN 'ดี' THEN 'good' WHEN 'ปานกลาง' THEN 'moderate'
              WHEN 'ไม่ดี' THEN 'poor' ELSE 'unknown' END AS airflow,
         IF(b3_wall_material_clean = 'ไม้', 'wood', 'other') AS wall,
         heat_impact_score
  FROM base
), cells AS (
  SELECT 'heatmap' AS kind, airflow AS dimension, wall AS label, count(*) AS households,
         CAST(NULL AS bigint) AS high, round(avg(heat_impact_score), 2) AS value
  FROM grid GROUP BY airflow, wall
), housing AS (
  SELECT CASE WHEN housing_heat_score BETWEEN 0 AND 1 THEN '0-1'
              WHEN housing_heat_score = 2 THEN '2'
              WHEN housing_heat_score = 3 THEN '3'
              WHEN housing_heat_score BETWEEN 4 AND 5 THEN '4-5'
              ELSE 'unknown' END AS band,
         heat_impact_score
  FROM base
), bands AS (
  SELECT 'housing' AS kind, 'score' AS dimension, band AS label, count(*) AS households,
         CAST(NULL AS bigint) AS high, round(avg(heat_impact_score), 2) AS value
  FROM housing GROUP BY band
), distribution AS (
  SELECT 'distribution' AS kind, 'impact' AS dimension, heat_impact_level AS label, count(*) AS households,
         CAST(NULL AS bigint) AS high, CAST(NULL AS double) AS value
  FROM base GROUP BY heat_impact_level
), single_metrics AS (
  SELECT * FROM features
  UNION ALL SELECT * FROM cells
  UNION ALL SELECT * FROM bands
  UNION ALL SELECT * FROM distribution
  UNION ALL SELECT * FROM feature_detail
  UNION ALL SELECT * FROM community
), combined AS (
  SELECT *, CAST(NULL AS bigint) AS low, CAST(NULL AS bigint) AS medium FROM single_metrics
  UNION ALL SELECT * FROM context
), disclosure AS (
  -- Suppress the entire family when any of its counts is small. This holds
  -- back complementary cells as well as rates and prevents subtraction.
  SELECT *, max(IF(households < 5 OR high BETWEEN 1 AND 4 OR households - high BETWEEN 1 AND 4
                           OR low BETWEEN 1 AND 4 OR medium BETWEEN 1 AND 4, 1, 0))
             OVER (PARTITION BY kind, IF(kind = 'heatmap', kind, dimension)) = 1 AS suppressed
  FROM combined
)
SELECT kind, dimension, label,
       IF(suppressed, NULL, households) AS households,
       IF(suppressed, NULL, high) AS high,
       IF(suppressed, NULL, value) AS value,
       suppressed,
       IF(suppressed, NULL, low) AS low,
       IF(suppressed, NULL, medium) AS medium
FROM disclosure
ORDER BY kind, dimension, label
