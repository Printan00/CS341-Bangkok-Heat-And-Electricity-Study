-- Q1: ลักษณะบ้านสัมพันธ์กับผลกระทบจากความร้อนอย่างไร (Happy Home เท่านั้น, usable_q1 = true)
-- ตัวผล: heat_impact_level (T10/D6: low 0-4, medium 5-7, high 8-13) ไม่ใช้ C2.1 เพราะ "ร้อนมากทุกวัน" 68/88 แทบไม่แปรผัน
-- ซ่อนทุกค่าที่ 1-4 บ้าน (<5) ถ้าแถวใดมีค่าที่ถูกซ่อน จะซ่อนทุกจำนวนและ % ในแถวนั้น
-- ผลเป็นความสัมพันธ์ ไม่ใช่เหตุและผล; ผลกระทบรายงานเอง ย้อนหลัง; รันด้วย workgroup bhes-wg database bhes

-- Q1.1 ลักษณะบ้านรายข้อ x ผลกระทบความร้อนสูง (heat_impact_level = high) เทียบไม่สูง (low/medium) รวม 2 ชุมชน; กลุ่มเล็กรวมเป็นหมวด (ดูชื่อหมวด)
WITH base AS (
  SELECT 'B4 หลังคา' AS feature, CASE WHEN b4_roof_material_clean = 'สังกะสี/เมทัลชีท' THEN 'สังกะสี/เมทัลชีท' ELSE 'กระเบื้อง/คอนกรีต/อื่น ๆ/ไม่ระบุ (รวม)' END AS level, heat_impact_level, heat_impact_score FROM bhes.happy_home_household WHERE usable_q1
    UNION ALL
    SELECT 'B3 วัสดุผนัง' AS feature, CASE WHEN b3_wall_material_clean = 'ไม้' THEN 'ไม้' WHEN b3_wall_material_clean = 'คอนกรีต' THEN 'คอนกรีต' ELSE 'ผสม/สังกะสี/อื่น ๆ/ไม่ระบุ (รวม)' END AS level, heat_impact_level, heat_impact_score FROM bhes.happy_home_household WHERE usable_q1
    UNION ALL
    SELECT 'B6 ฝ้าเพดาน' AS feature, CASE WHEN b6_ceiling_clean = 'ไม่มี' THEN 'ไม่มีฝ้า' ELSE 'มีฝ้า/ไม่แน่ใจ (รวม)' END AS level, heat_impact_level, heat_impact_score FROM bhes.happy_home_household WHERE usable_q1
    UNION ALL
    SELECT 'B7 ฉนวน' AS feature, CASE WHEN b7_insulation_clean = 'ไม่มี' THEN 'ไม่มีฉนวน' ELSE 'มีฉนวน/ไม่แน่ใจ (รวม)' END AS level, heat_impact_level, heat_impact_score FROM bhes.happy_home_household WHERE usable_q1
    UNION ALL
    SELECT 'B8 ระบายอากาศ' AS feature, coalesce(b8_ventilation_clean, '(ไม่ระบุ/ไม่แน่ใจ)') AS level, heat_impact_level, heat_impact_score FROM bhes.happy_home_household WHERE usable_q1
    UNION ALL
    SELECT 'B9 ร่มเงา' AS feature, coalesce(b9_shade_clean, '(ไม่ระบุ/ไม่แน่ใจ)') AS level, heat_impact_level, heat_impact_score FROM bhes.happy_home_household WHERE usable_q1
    UNION ALL
    SELECT 'B1 ประเภทที่อยู่' AS feature, CASE WHEN b1_housing_type_clean IN ('บ้านเดี่ยว', 'บ้านแถว/ทาวน์เฮาส์') THEN b1_housing_type_clean ELSE 'ห้องเช่า/แฟลต/ชั่วคราว/อื่น ๆ (รวม)' END AS level, heat_impact_level, heat_impact_score FROM bhes.happy_home_household WHERE usable_q1
), cells0 AS (
  SELECT feature AS feature, level AS level,
    count(*) AS n,
    count_if(heat_impact_level = 'high') AS c_high,
    count_if(heat_impact_level IN ('low', 'medium')) AS c_not_high,
    count_if(heat_impact_level IS NULL) AS c_heat_missing,
    avg(heat_impact_score) AS avg_score
  FROM base
  GROUP BY 1, 2
), cells AS (
  SELECT *,
  CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END AS hid,
  SUM(CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END) OVER (PARTITION BY feature) AS n_hidden,
  ROW_NUMBER() OVER (PARTITION BY feature ORDER BY CASE WHEN n BETWEEN 1 AND 4 THEN 1000000 ELSE n END, feature, level) AS rn_small FROM cells0
), flagged AS (
  SELECT *, (hid = 1 OR (n_hidden = 1 AND rn_small = 1)) AS sup FROM cells
)
SELECT feature, level,
  CASE WHEN NOT sup THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_not_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(c_high AS varchar) ELSE '<5' END AS n_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_not_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_high / n, 1) AS varchar) ELSE '<5' END AS pct_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_not_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(c_not_high AS varchar) ELSE '<5' END AS n_not_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_not_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_not_high / n, 1) AS varchar) ELSE '<5' END AS pct_not_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_not_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(c_heat_missing AS varchar) ELSE '<5' END AS n_heat_missing,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_not_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_heat_missing / n, 1) AS varchar) ELSE '<5' END AS pct_heat_missing,
  CASE WHEN NOT sup THEN CAST(ROUND(avg_score, 2) AS varchar) ELSE '<5' END AS avg_heat_score
FROM flagged
ORDER BY feature, level;

-- Q1.2 คะแนนสภาพบ้านเสี่ยงร้อน (housing_heat_score 0-5 จัดเป็นช่วง 0-1 / 2 / 3 / 4-5; null เมื่อตอบชัดน้อยกว่า 4 ข้อ) x ผลกระทบความร้อนสูง
WITH base AS (
  SELECT * FROM bhes.happy_home_household WHERE usable_q1
), cells0 AS (
  SELECT CASE WHEN housing_heat_score IS NULL THEN '(null)' WHEN housing_heat_score <= 1 THEN '0-1' WHEN housing_heat_score = 2 THEN '2' WHEN housing_heat_score = 3 THEN '3' ELSE '4-5' END AS housing_heat_score_band,
    count(*) AS n,
    count_if(heat_impact_level = 'high') AS c_high,
    count_if(heat_impact_level IN ('low', 'medium')) AS c_not_high,
    count_if(heat_impact_level IS NULL) AS c_heat_missing,
    avg(heat_impact_score) AS avg_score
  FROM base
  GROUP BY 1
), cells AS (
  SELECT *,
  CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END AS hid,
  SUM(CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END) OVER () AS n_hidden,
  ROW_NUMBER() OVER ( ORDER BY CASE WHEN n BETWEEN 1 AND 4 THEN 1000000 ELSE n END, housing_heat_score_band) AS rn_small FROM cells0
), flagged AS (
  SELECT *, (hid = 1 OR (n_hidden = 1 AND rn_small = 1)) AS sup FROM cells
)
SELECT housing_heat_score_band,
  CASE WHEN NOT sup THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_not_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(c_high AS varchar) ELSE '<5' END AS n_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_not_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_high / n, 1) AS varchar) ELSE '<5' END AS pct_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_not_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(c_not_high AS varchar) ELSE '<5' END AS n_not_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_not_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_not_high / n, 1) AS varchar) ELSE '<5' END AS pct_not_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_not_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(c_heat_missing AS varchar) ELSE '<5' END AS n_heat_missing,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_not_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_heat_missing / n, 1) AS varchar) ELSE '<5' END AS pct_heat_missing,
  CASE WHEN NOT sup THEN CAST(ROUND(avg_score, 2) AS varchar) ELSE '<5' END AS avg_heat_score
FROM flagged
ORDER BY housing_heat_score_band;

-- Q1.3 ตัวตรวจ: ผลกระทบความร้อนแยกตามชุมชน (community_key) ว่าสองชุมชนต่างกันหรือไม่
WITH base AS (
  SELECT * FROM bhes.happy_home_household WHERE usable_q1
), cells0 AS (
  SELECT community_key AS community_key,
    count(*) AS n,
    count_if(heat_impact_level = 'low') AS c_low,
    count_if(heat_impact_level = 'medium') AS c_medium,
    count_if(heat_impact_level = 'high') AS c_high,
    count_if(heat_impact_level IS NULL) AS c_heat_missing
  FROM base
  GROUP BY 1
), cells AS (
  SELECT *,
  CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END AS hid,
  SUM(CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END) OVER () AS n_hidden,
  ROW_NUMBER() OVER ( ORDER BY CASE WHEN n BETWEEN 1 AND 4 THEN 1000000 ELSE n END, community_key) AS rn_small FROM cells0
), flagged AS (
  SELECT *, (hid = 1 OR (n_hidden = 1 AND rn_small = 1)) AS sup FROM cells
)
SELECT community_key,
  CASE WHEN NOT sup THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN (NOT sup AND NOT (c_low BETWEEN 1 AND 4 OR c_medium BETWEEN 1 AND 4 OR c_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(c_low AS varchar) ELSE '<5' END AS n_low,
  CASE WHEN (NOT sup AND NOT (c_low BETWEEN 1 AND 4 OR c_medium BETWEEN 1 AND 4 OR c_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_low / n, 1) AS varchar) ELSE '<5' END AS pct_low,
  CASE WHEN (NOT sup AND NOT (c_low BETWEEN 1 AND 4 OR c_medium BETWEEN 1 AND 4 OR c_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(c_medium AS varchar) ELSE '<5' END AS n_medium,
  CASE WHEN (NOT sup AND NOT (c_low BETWEEN 1 AND 4 OR c_medium BETWEEN 1 AND 4 OR c_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_medium / n, 1) AS varchar) ELSE '<5' END AS pct_medium,
  CASE WHEN (NOT sup AND NOT (c_low BETWEEN 1 AND 4 OR c_medium BETWEEN 1 AND 4 OR c_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(c_high AS varchar) ELSE '<5' END AS n_high,
  CASE WHEN (NOT sup AND NOT (c_low BETWEEN 1 AND 4 OR c_medium BETWEEN 1 AND 4 OR c_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_high / n, 1) AS varchar) ELSE '<5' END AS pct_high,
  CASE WHEN (NOT sup AND NOT (c_low BETWEEN 1 AND 4 OR c_medium BETWEEN 1 AND 4 OR c_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(c_heat_missing AS varchar) ELSE '<5' END AS n_heat_missing,
  CASE WHEN (NOT sup AND NOT (c_low BETWEEN 1 AND 4 OR c_medium BETWEEN 1 AND 4 OR c_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_heat_missing / n, 1) AS varchar) ELSE '<5' END AS pct_heat_missing
FROM flagged
ORDER BY community_key;

-- Q1.4 ครัวเรือนที่รับมือได้จำกัด (coping_limited: >= 3 จาก 6 ด้าน) x ระดับผลกระทบ
WITH base AS (
  SELECT * FROM bhes.happy_home_household WHERE usable_q1
), cells0 AS (
  SELECT coalesce(CAST(coping_limited AS varchar), '(null)') AS coping_limited,
    count(*) AS n,
    count_if(heat_impact_level = 'low') AS c_low,
    count_if(heat_impact_level = 'medium') AS c_medium,
    count_if(heat_impact_level = 'high') AS c_high,
    count_if(heat_impact_level IS NULL) AS c_heat_missing
  FROM base
  GROUP BY 1
), cells AS (
  SELECT *,
  CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END AS hid,
  SUM(CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END) OVER () AS n_hidden,
  ROW_NUMBER() OVER ( ORDER BY CASE WHEN n BETWEEN 1 AND 4 THEN 1000000 ELSE n END, coping_limited) AS rn_small FROM cells0
), flagged AS (
  SELECT *, (hid = 1 OR (n_hidden = 1 AND rn_small = 1)) AS sup FROM cells
)
SELECT coping_limited,
  CASE WHEN NOT sup THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN (NOT sup AND NOT (c_low BETWEEN 1 AND 4 OR c_medium BETWEEN 1 AND 4 OR c_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(c_low AS varchar) ELSE '<5' END AS n_low,
  CASE WHEN (NOT sup AND NOT (c_low BETWEEN 1 AND 4 OR c_medium BETWEEN 1 AND 4 OR c_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_low / n, 1) AS varchar) ELSE '<5' END AS pct_low,
  CASE WHEN (NOT sup AND NOT (c_low BETWEEN 1 AND 4 OR c_medium BETWEEN 1 AND 4 OR c_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(c_medium AS varchar) ELSE '<5' END AS n_medium,
  CASE WHEN (NOT sup AND NOT (c_low BETWEEN 1 AND 4 OR c_medium BETWEEN 1 AND 4 OR c_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_medium / n, 1) AS varchar) ELSE '<5' END AS pct_medium,
  CASE WHEN (NOT sup AND NOT (c_low BETWEEN 1 AND 4 OR c_medium BETWEEN 1 AND 4 OR c_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(c_high AS varchar) ELSE '<5' END AS n_high,
  CASE WHEN (NOT sup AND NOT (c_low BETWEEN 1 AND 4 OR c_medium BETWEEN 1 AND 4 OR c_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_high / n, 1) AS varchar) ELSE '<5' END AS pct_high,
  CASE WHEN (NOT sup AND NOT (c_low BETWEEN 1 AND 4 OR c_medium BETWEEN 1 AND 4 OR c_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(c_heat_missing AS varchar) ELSE '<5' END AS n_heat_missing,
  CASE WHEN (NOT sup AND NOT (c_low BETWEEN 1 AND 4 OR c_medium BETWEEN 1 AND 4 OR c_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_heat_missing / n, 1) AS varchar) ELSE '<5' END AS pct_heat_missing
FROM flagged
ORDER BY coping_limited;

-- Q1.5 สภาพบ้านเสี่ยงสูง (housing_heat_score >= 3) เทียบ ต่ำกว่า x ระดับผลกระทบ
WITH base AS (
  SELECT * FROM bhes.happy_home_household WHERE usable_q1
), cells0 AS (
  SELECT CASE WHEN housing_heat_score IS NULL THEN '(null)' WHEN housing_heat_score >= 3 THEN '3-5 (เสี่ยงสูง)' ELSE '0-2' END AS housing_risk_group,
    count(*) AS n,
    count_if(heat_impact_level = 'low') AS c_low,
    count_if(heat_impact_level = 'medium') AS c_medium,
    count_if(heat_impact_level = 'high') AS c_high,
    count_if(heat_impact_level IS NULL) AS c_heat_missing
  FROM base
  GROUP BY 1
), cells AS (
  SELECT *,
  CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END AS hid,
  SUM(CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END) OVER () AS n_hidden,
  ROW_NUMBER() OVER ( ORDER BY CASE WHEN n BETWEEN 1 AND 4 THEN 1000000 ELSE n END, housing_risk_group) AS rn_small FROM cells0
), flagged AS (
  SELECT *, (hid = 1 OR (n_hidden = 1 AND rn_small = 1)) AS sup FROM cells
)
SELECT housing_risk_group,
  CASE WHEN NOT sup THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN (NOT sup AND NOT (c_low BETWEEN 1 AND 4 OR c_medium BETWEEN 1 AND 4 OR c_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(c_low AS varchar) ELSE '<5' END AS n_low,
  CASE WHEN (NOT sup AND NOT (c_low BETWEEN 1 AND 4 OR c_medium BETWEEN 1 AND 4 OR c_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_low / n, 1) AS varchar) ELSE '<5' END AS pct_low,
  CASE WHEN (NOT sup AND NOT (c_low BETWEEN 1 AND 4 OR c_medium BETWEEN 1 AND 4 OR c_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(c_medium AS varchar) ELSE '<5' END AS n_medium,
  CASE WHEN (NOT sup AND NOT (c_low BETWEEN 1 AND 4 OR c_medium BETWEEN 1 AND 4 OR c_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_medium / n, 1) AS varchar) ELSE '<5' END AS pct_medium,
  CASE WHEN (NOT sup AND NOT (c_low BETWEEN 1 AND 4 OR c_medium BETWEEN 1 AND 4 OR c_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(c_high AS varchar) ELSE '<5' END AS n_high,
  CASE WHEN (NOT sup AND NOT (c_low BETWEEN 1 AND 4 OR c_medium BETWEEN 1 AND 4 OR c_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_high / n, 1) AS varchar) ELSE '<5' END AS pct_high,
  CASE WHEN (NOT sup AND NOT (c_low BETWEEN 1 AND 4 OR c_medium BETWEEN 1 AND 4 OR c_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(c_heat_missing AS varchar) ELSE '<5' END AS n_heat_missing,
  CASE WHEN (NOT sup AND NOT (c_low BETWEEN 1 AND 4 OR c_medium BETWEEN 1 AND 4 OR c_high BETWEEN 1 AND 4 OR c_heat_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_heat_missing / n, 1) AS varchar) ELSE '<5' END AS pct_heat_missing
FROM flagged
ORDER BY housing_risk_group;

-- Q1.6 Heatmap: การระบายอากาศ (B8) x วัสดุผนัง (ไม้ เทียบ อื่น ๆ) -> คะแนนผลกระทบความร้อนเฉลี่ย (0-13) และจำนวนครัวเรือน
-- ทุกช่องมีมากกว่า 5 บ้าน ค่าเฉลี่ยของกลุ่มตั้งแต่ 5 บ้านขึ้นไปไม่เปิดเผยจำนวนเล็ก; ช่องที่ n < 5 แสดงเป็น '<5'
WITH cells AS (
  SELECT
    coalesce(b8_ventilation_clean, '(ไม่ระบุ/ไม่แน่ใจ)') AS ventilation,
    CASE WHEN b3_wall_material_clean = 'ไม้' THEN 'ไม้' ELSE 'อื่น ๆ (คอนกรีต/ผสม/สังกะสี/ไม่ระบุ)' END AS wall,
    count(*) AS n,
    avg(heat_impact_score) AS avg_score
  FROM bhes.happy_home_household
  WHERE usable_q1
  GROUP BY 1, 2
)
SELECT ventilation, wall,
  CASE WHEN n >= 5 THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN n >= 5 THEN CAST(ROUND(avg_score, 2) AS varchar) ELSE '<5' END AS avg_heat_score
FROM cells
ORDER BY ventilation, wall;
