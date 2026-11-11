-- Q2: ภาระค่าไฟเทียบรายได้แตกต่างกันอย่างไร ระหว่างกลุ่มรายได้ และระหว่างครัวเรือนที่เข้าถึงการทำความเย็นต่างกัน
-- ภาระ = ค่าไฟหน้าร้อน (E1.2) / รายได้ต่อเดือน เป็นช่วง: burden_min = bill_min / income_max, burden_max = bill_max / income_min (T07)
-- ช่วงปลายเปิดใช้เพดาน D1 (รายได้ <5,000 -> 2,500; >50,000 -> 100,000; ค่าไฟ >3,000 -> 6,000) burden_class: high = burden_min >= 10% (D2)
-- ค่า burden_*_pct เป็นเปอร์เซ็นต์; ซ่อนทุกค่าที่ 1-4 บ้าน; ผลเป็นความสัมพันธ์ ไม่ใช่เหตุและผล

-- Q2.1 ชั้นรายได้ (A7) x ภาระค่าไฟหน้าร้อน (เกณฑ์ 10%)
WITH base AS (
  SELECT * FROM bhes.happy_home_household WHERE usable_q2
), cells0 AS (
  SELECT coalesce(income_ord, 0) AS income_ord, coalesce(a7_income_band_clean, '(ไม่ระบุ)') AS income_band,
    count(*) AS n,
    count_if(burden_class = 'high') AS c_high,
    count_if(burden_class = 'possibly_high') AS c_possibly_high,
    count_if(burden_class = 'low') AS c_low,
    count_if(burden_class IS NULL) AS c_burden_missing,
    min(burden_min) AS b_min_lo, approx_percentile(burden_min, 0.5) AS b_min_med, max(burden_max) AS b_max_hi,
    approx_percentile(burden_max, 0.5) AS b_max_med
  FROM base
  GROUP BY 1, 2
), cells AS (
  SELECT *,
  CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END AS hid,
  SUM(CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END) OVER () AS n_hidden,
  ROW_NUMBER() OVER ( ORDER BY CASE WHEN n BETWEEN 1 AND 4 THEN 1000000 ELSE n END, income_ord, income_band) AS rn_small FROM cells0
), flagged AS (
  SELECT *, (hid = 1 OR (n_hidden = 1 AND rn_small = 1)) AS sup FROM cells
)
SELECT income_ord, income_band,
  CASE WHEN NOT sup THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_high AS varchar) ELSE '<5' END AS n_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_high / n, 1) AS varchar) ELSE '<5' END AS pct_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_possibly_high AS varchar) ELSE '<5' END AS n_possibly_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_possibly_high / n, 1) AS varchar) ELSE '<5' END AS pct_possibly_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_low AS varchar) ELSE '<5' END AS n_low,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_low / n, 1) AS varchar) ELSE '<5' END AS pct_low,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_burden_missing AS varchar) ELSE '<5' END AS n_burden_missing,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_burden_missing / n, 1) AS varchar) ELSE '<5' END AS pct_burden_missing,
  CASE WHEN NOT sup THEN CAST(ROUND(100 * b_min_lo, 1) AS varchar) ELSE '<5' END AS burden_min_lowest_pct,
  CASE WHEN NOT sup THEN CAST(ROUND(100 * b_min_med, 1) AS varchar) ELSE '<5' END AS burden_min_median_pct,
  CASE WHEN NOT sup THEN CAST(ROUND(100 * b_max_med, 1) AS varchar) ELSE '<5' END AS burden_max_median_pct,
  CASE WHEN NOT sup THEN CAST(ROUND(100 * b_max_hi, 1) AS varchar) ELSE '<5' END AS burden_max_highest_pct
FROM flagged
ORDER BY income_ord, income_band;

-- Q2.2 ชั้นรายได้ x ภาระค่าไฟ ที่เกณฑ์ 6% (ทดสอบความไว D2)
WITH base AS (
  SELECT * FROM bhes.happy_home_household WHERE usable_q2
), cells0 AS (
  SELECT coalesce(income_ord, 0) AS income_ord, coalesce(a7_income_band_clean, '(ไม่ระบุ)') AS income_band,
    count(*) AS n,
    count_if(burden_class_6pct = 'high') AS c_high,
    count_if(burden_class_6pct = 'possibly_high') AS c_possibly_high,
    count_if(burden_class_6pct = 'low') AS c_low,
    count_if(burden_class_6pct IS NULL) AS c_burden_missing
  FROM base
  GROUP BY 1, 2
), cells AS (
  SELECT *,
  CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END AS hid,
  SUM(CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END) OVER () AS n_hidden,
  ROW_NUMBER() OVER ( ORDER BY CASE WHEN n BETWEEN 1 AND 4 THEN 1000000 ELSE n END, income_ord, income_band) AS rn_small FROM cells0
), flagged AS (
  SELECT *, (hid = 1 OR (n_hidden = 1 AND rn_small = 1)) AS sup FROM cells
)
SELECT income_ord, income_band,
  CASE WHEN NOT sup THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_high AS varchar) ELSE '<5' END AS n_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_high / n, 1) AS varchar) ELSE '<5' END AS pct_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_possibly_high AS varchar) ELSE '<5' END AS n_possibly_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_possibly_high / n, 1) AS varchar) ELSE '<5' END AS pct_possibly_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_low AS varchar) ELSE '<5' END AS n_low,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_low / n, 1) AS varchar) ELSE '<5' END AS pct_low,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_burden_missing AS varchar) ELSE '<5' END AS n_burden_missing,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_burden_missing / n, 1) AS varchar) ELSE '<5' END AS pct_burden_missing
FROM flagged
ORDER BY income_ord, income_band;

-- Q2.3 การเข้าถึงการทำความเย็น: มีแอร์ (has_aircon) x ภาระค่าไฟ
WITH base AS (
  SELECT * FROM bhes.happy_home_household WHERE usable_q2
), cells0 AS (
  SELECT coalesce(CAST(has_aircon AS varchar), '(null)') AS has_aircon,
    count(*) AS n,
    count_if(burden_class = 'high') AS c_high,
    count_if(burden_class = 'possibly_high') AS c_possibly_high,
    count_if(burden_class = 'low') AS c_low,
    count_if(burden_class IS NULL) AS c_burden_missing,
    min(burden_min) AS b_min_lo, approx_percentile(burden_min, 0.5) AS b_min_med, max(burden_max) AS b_max_hi,
    approx_percentile(burden_max, 0.5) AS b_max_med
  FROM base
  GROUP BY 1
), cells AS (
  SELECT *,
  CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END AS hid,
  SUM(CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END) OVER () AS n_hidden,
  ROW_NUMBER() OVER ( ORDER BY CASE WHEN n BETWEEN 1 AND 4 THEN 1000000 ELSE n END, has_aircon) AS rn_small FROM cells0
), flagged AS (
  SELECT *, (hid = 1 OR (n_hidden = 1 AND rn_small = 1)) AS sup FROM cells
)
SELECT has_aircon,
  CASE WHEN NOT sup THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_high AS varchar) ELSE '<5' END AS n_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_high / n, 1) AS varchar) ELSE '<5' END AS pct_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_possibly_high AS varchar) ELSE '<5' END AS n_possibly_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_possibly_high / n, 1) AS varchar) ELSE '<5' END AS pct_possibly_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_low AS varchar) ELSE '<5' END AS n_low,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_low / n, 1) AS varchar) ELSE '<5' END AS pct_low,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_burden_missing AS varchar) ELSE '<5' END AS n_burden_missing,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_burden_missing / n, 1) AS varchar) ELSE '<5' END AS pct_burden_missing,
  CASE WHEN NOT sup THEN CAST(ROUND(100 * b_min_lo, 1) AS varchar) ELSE '<5' END AS burden_min_lowest_pct,
  CASE WHEN NOT sup THEN CAST(ROUND(100 * b_min_med, 1) AS varchar) ELSE '<5' END AS burden_min_median_pct,
  CASE WHEN NOT sup THEN CAST(ROUND(100 * b_max_med, 1) AS varchar) ELSE '<5' END AS burden_max_median_pct,
  CASE WHEN NOT sup THEN CAST(ROUND(100 * b_max_hi, 1) AS varchar) ELSE '<5' END AS burden_max_highest_pct
FROM flagged
ORDER BY has_aircon;

-- Q2.4 ชั้นรายได้ x มีแอร์ x ภาระค่าไฟ
WITH base AS (
  SELECT * FROM bhes.happy_home_household WHERE usable_q2
), cells0 AS (
  SELECT coalesce(income_ord, 0) AS income_ord, coalesce(CAST(has_aircon AS varchar), '(null)') AS has_aircon,
    count(*) AS n,
    count_if(burden_class = 'high') AS c_high,
    count_if(burden_class = 'possibly_high') AS c_possibly_high,
    count_if(burden_class = 'low') AS c_low,
    count_if(burden_class IS NULL) AS c_burden_missing
  FROM base
  GROUP BY 1, 2
), cells AS (
  SELECT *,
  CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END AS hid,
  SUM(CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END) OVER () AS n_hidden,
  ROW_NUMBER() OVER ( ORDER BY CASE WHEN n BETWEEN 1 AND 4 THEN 1000000 ELSE n END, income_ord, has_aircon) AS rn_small FROM cells0
), flagged AS (
  SELECT *, (hid = 1 OR (n_hidden = 1 AND rn_small = 1)) AS sup FROM cells
)
SELECT income_ord, has_aircon,
  CASE WHEN NOT sup THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_high AS varchar) ELSE '<5' END AS n_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_high / n, 1) AS varchar) ELSE '<5' END AS pct_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_possibly_high AS varchar) ELSE '<5' END AS n_possibly_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_possibly_high / n, 1) AS varchar) ELSE '<5' END AS pct_possibly_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_low AS varchar) ELSE '<5' END AS n_low,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_low / n, 1) AS varchar) ELSE '<5' END AS pct_low,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_burden_missing AS varchar) ELSE '<5' END AS n_burden_missing,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_burden_missing / n, 1) AS varchar) ELSE '<5' END AS pct_burden_missing
FROM flagged
ORDER BY income_ord, has_aircon;

-- Q2.5 ชั้นค่าไฟหน้าร้อน (E1.2) x ภาระค่าไฟ
WITH base AS (
  SELECT * FROM bhes.happy_home_household WHERE usable_q2
), cells0 AS (
  SELECT coalesce(bill_summer_ord, 0) AS bill_summer_ord, coalesce(e1_2_bill_summer_band_clean, '(ไม่ระบุ)') AS bill_summer_band,
    count(*) AS n,
    count_if(burden_class = 'high') AS c_high,
    count_if(burden_class = 'possibly_high') AS c_possibly_high,
    count_if(burden_class = 'low') AS c_low,
    count_if(burden_class IS NULL) AS c_burden_missing
  FROM base
  GROUP BY 1, 2
), cells AS (
  SELECT *,
  CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END AS hid,
  SUM(CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END) OVER () AS n_hidden,
  ROW_NUMBER() OVER ( ORDER BY CASE WHEN n BETWEEN 1 AND 4 THEN 1000000 ELSE n END, bill_summer_ord, bill_summer_band) AS rn_small FROM cells0
), flagged AS (
  SELECT *, (hid = 1 OR (n_hidden = 1 AND rn_small = 1)) AS sup FROM cells
)
SELECT bill_summer_ord, bill_summer_band,
  CASE WHEN NOT sup THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_high AS varchar) ELSE '<5' END AS n_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_high / n, 1) AS varchar) ELSE '<5' END AS pct_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_possibly_high AS varchar) ELSE '<5' END AS n_possibly_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_possibly_high / n, 1) AS varchar) ELSE '<5' END AS pct_possibly_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_low AS varchar) ELSE '<5' END AS n_low,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_low / n, 1) AS varchar) ELSE '<5' END AS pct_low,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_burden_missing AS varchar) ELSE '<5' END AS n_burden_missing,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_burden_missing / n, 1) AS varchar) ELSE '<5' END AS pct_burden_missing
FROM flagged
ORDER BY bill_summer_ord, bill_summer_band;

-- Q2.6 ค่าไฟหน้าร้อนเพิ่มจากช่วงปกติเท่าไร (E1.3) x ภาระค่าไฟ
WITH base AS (
  SELECT * FROM bhes.happy_home_household WHERE usable_q2
), cells0 AS (
  SELECT coalesce(e1_3_summer_bill_increase_clean, '(ไม่ระบุ/ไม่แน่ใจ)') AS summer_increase,
    count(*) AS n,
    count_if(burden_class = 'high') AS c_high,
    count_if(burden_class = 'possibly_high') AS c_possibly_high,
    count_if(burden_class = 'low') AS c_low,
    count_if(burden_class IS NULL) AS c_burden_missing
  FROM base
  GROUP BY 1
), cells AS (
  SELECT *,
  CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END AS hid,
  SUM(CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END) OVER () AS n_hidden,
  ROW_NUMBER() OVER ( ORDER BY CASE WHEN n BETWEEN 1 AND 4 THEN 1000000 ELSE n END, summer_increase) AS rn_small FROM cells0
), flagged AS (
  SELECT *, (hid = 1 OR (n_hidden = 1 AND rn_small = 1)) AS sup FROM cells
)
SELECT summer_increase,
  CASE WHEN NOT sup THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_high AS varchar) ELSE '<5' END AS n_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_high / n, 1) AS varchar) ELSE '<5' END AS pct_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_possibly_high AS varchar) ELSE '<5' END AS n_possibly_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_possibly_high / n, 1) AS varchar) ELSE '<5' END AS pct_possibly_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_low AS varchar) ELSE '<5' END AS n_low,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_low / n, 1) AS varchar) ELSE '<5' END AS pct_low,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_burden_missing AS varchar) ELSE '<5' END AS n_burden_missing,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_burden_missing / n, 1) AS varchar) ELSE '<5' END AS pct_burden_missing
FROM flagged
ORDER BY summer_increase;

-- Q2.7 การใช้พัดลม (e2_1_fan) x ภาระค่าไฟ
WITH base AS (
  SELECT * FROM bhes.happy_home_household WHERE usable_q2
), cells0 AS (
  SELECT coalesce(CAST(e2_1_fan AS varchar), '(null)') AS has_fan,
    count(*) AS n,
    count_if(burden_class = 'high') AS c_high,
    count_if(burden_class = 'possibly_high') AS c_possibly_high,
    count_if(burden_class = 'low') AS c_low,
    count_if(burden_class IS NULL) AS c_burden_missing
  FROM base
  GROUP BY 1
), cells AS (
  SELECT *,
  CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END AS hid,
  SUM(CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END) OVER () AS n_hidden,
  ROW_NUMBER() OVER ( ORDER BY CASE WHEN n BETWEEN 1 AND 4 THEN 1000000 ELSE n END, has_fan) AS rn_small FROM cells0
), flagged AS (
  SELECT *, (hid = 1 OR (n_hidden = 1 AND rn_small = 1)) AS sup FROM cells
)
SELECT has_fan,
  CASE WHEN NOT sup THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_high AS varchar) ELSE '<5' END AS n_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_high / n, 1) AS varchar) ELSE '<5' END AS pct_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_possibly_high AS varchar) ELSE '<5' END AS n_possibly_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_possibly_high / n, 1) AS varchar) ELSE '<5' END AS pct_possibly_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_low AS varchar) ELSE '<5' END AS n_low,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_low / n, 1) AS varchar) ELSE '<5' END AS pct_low,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_burden_missing AS varchar) ELSE '<5' END AS n_burden_missing,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_burden_missing / n, 1) AS varchar) ELSE '<5' END AS pct_burden_missing
FROM flagged
ORDER BY has_fan;

-- Q2.8 ตัวตรวจ: ภาระค่าไฟแยกตามชุมชน
WITH base AS (
  SELECT * FROM bhes.happy_home_household WHERE usable_q2
), cells0 AS (
  SELECT community_key AS community_key,
    count(*) AS n,
    count_if(burden_class = 'high') AS c_high,
    count_if(burden_class = 'possibly_high') AS c_possibly_high,
    count_if(burden_class = 'low') AS c_low,
    count_if(burden_class IS NULL) AS c_burden_missing
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
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_high AS varchar) ELSE '<5' END AS n_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_high / n, 1) AS varchar) ELSE '<5' END AS pct_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_possibly_high AS varchar) ELSE '<5' END AS n_possibly_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_possibly_high / n, 1) AS varchar) ELSE '<5' END AS pct_possibly_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_low AS varchar) ELSE '<5' END AS n_low,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_low / n, 1) AS varchar) ELSE '<5' END AS pct_low,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_burden_missing AS varchar) ELSE '<5' END AS n_burden_missing,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_burden_missing / n, 1) AS varchar) ELSE '<5' END AS pct_burden_missing
FROM flagged
ORDER BY community_key;

-- Q2.9 ชั้นรายได้รวมเป็น 3 กลุ่ม (ไม่เกิน 10,000 / 10,001-20,000 / มากกว่า 20,000) x ภาระค่าไฟหน้าร้อน (เกณฑ์ 10%)
WITH base AS (
  SELECT * FROM bhes.happy_home_household WHERE usable_q2
), cells0 AS (
  SELECT CASE WHEN income_ord IS NULL THEN '(null)' WHEN income_ord <= 2 THEN '1) ไม่เกิน 10,000' WHEN income_ord = 3 THEN '2) 10,001-20,000' ELSE '3) มากกว่า 20,000' END AS income_group,
    count(*) AS n,
    count_if(burden_class = 'high') AS c_high,
    count_if(burden_class = 'possibly_high') AS c_possibly_high,
    count_if(burden_class = 'low') AS c_low,
    count_if(burden_class IS NULL) AS c_burden_missing,
    min(burden_min) AS b_min_lo, approx_percentile(burden_min, 0.5) AS b_min_med, max(burden_max) AS b_max_hi,
    approx_percentile(burden_max, 0.5) AS b_max_med
  FROM base
  GROUP BY 1
), cells AS (
  SELECT *,
  CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END AS hid,
  SUM(CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END) OVER () AS n_hidden,
  ROW_NUMBER() OVER ( ORDER BY CASE WHEN n BETWEEN 1 AND 4 THEN 1000000 ELSE n END, income_group) AS rn_small FROM cells0
), flagged AS (
  SELECT *, (hid = 1 OR (n_hidden = 1 AND rn_small = 1)) AS sup FROM cells
)
SELECT income_group,
  CASE WHEN NOT sup THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_high AS varchar) ELSE '<5' END AS n_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_high / n, 1) AS varchar) ELSE '<5' END AS pct_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_possibly_high AS varchar) ELSE '<5' END AS n_possibly_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_possibly_high / n, 1) AS varchar) ELSE '<5' END AS pct_possibly_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_low AS varchar) ELSE '<5' END AS n_low,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_low / n, 1) AS varchar) ELSE '<5' END AS pct_low,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_burden_missing AS varchar) ELSE '<5' END AS n_burden_missing,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_burden_missing / n, 1) AS varchar) ELSE '<5' END AS pct_burden_missing,
  CASE WHEN NOT sup THEN CAST(ROUND(100 * b_min_lo, 1) AS varchar) ELSE '<5' END AS burden_min_lowest_pct,
  CASE WHEN NOT sup THEN CAST(ROUND(100 * b_min_med, 1) AS varchar) ELSE '<5' END AS burden_min_median_pct,
  CASE WHEN NOT sup THEN CAST(ROUND(100 * b_max_med, 1) AS varchar) ELSE '<5' END AS burden_max_median_pct,
  CASE WHEN NOT sup THEN CAST(ROUND(100 * b_max_hi, 1) AS varchar) ELSE '<5' END AS burden_max_highest_pct
FROM flagged
ORDER BY income_group;

-- Q2.10 ชั้นรายได้ 3 กลุ่ม x มีแอร์ x ภาระค่าไฟ (เกณฑ์ 10%)
WITH base AS (
  SELECT * FROM bhes.happy_home_household WHERE usable_q2
), cells0 AS (
  SELECT CASE WHEN income_ord IS NULL THEN '(null)' WHEN income_ord <= 2 THEN '1) ไม่เกิน 10,000' WHEN income_ord = 3 THEN '2) 10,001-20,000' ELSE '3) มากกว่า 20,000' END AS income_group, coalesce(CAST(has_aircon AS varchar), '(null)') AS has_aircon,
    count(*) AS n,
    count_if(burden_class = 'high') AS c_high,
    count_if(burden_class = 'possibly_high') AS c_possibly_high,
    count_if(burden_class = 'low') AS c_low,
    count_if(burden_class IS NULL) AS c_burden_missing
  FROM base
  GROUP BY 1, 2
), cells AS (
  SELECT *,
  CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END AS hid,
  SUM(CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END) OVER () AS n_hidden,
  ROW_NUMBER() OVER ( ORDER BY CASE WHEN n BETWEEN 1 AND 4 THEN 1000000 ELSE n END, income_group, has_aircon) AS rn_small FROM cells0
), flagged AS (
  SELECT *, (hid = 1 OR (n_hidden = 1 AND rn_small = 1)) AS sup FROM cells
)
SELECT income_group, has_aircon,
  CASE WHEN NOT sup THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_high AS varchar) ELSE '<5' END AS n_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_high / n, 1) AS varchar) ELSE '<5' END AS pct_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_possibly_high AS varchar) ELSE '<5' END AS n_possibly_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_possibly_high / n, 1) AS varchar) ELSE '<5' END AS pct_possibly_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_low AS varchar) ELSE '<5' END AS n_low,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_low / n, 1) AS varchar) ELSE '<5' END AS pct_low,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_burden_missing AS varchar) ELSE '<5' END AS n_burden_missing,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_burden_missing / n, 1) AS varchar) ELSE '<5' END AS pct_burden_missing
FROM flagged
ORDER BY income_group, has_aircon;

-- Q2.11 ชั้นรายได้ 3 กลุ่ม x ภาระค่าไฟ ที่เกณฑ์ 6% (ทดสอบความไว D2)
WITH base AS (
  SELECT * FROM bhes.happy_home_household WHERE usable_q2
), cells0 AS (
  SELECT CASE WHEN income_ord IS NULL THEN '(null)' WHEN income_ord <= 2 THEN '1) ไม่เกิน 10,000' WHEN income_ord = 3 THEN '2) 10,001-20,000' ELSE '3) มากกว่า 20,000' END AS income_group,
    count(*) AS n,
    count_if(burden_class_6pct = 'high') AS c_high,
    count_if(burden_class_6pct = 'possibly_high') AS c_possibly_high,
    count_if(burden_class_6pct = 'low') AS c_low,
    count_if(burden_class_6pct IS NULL) AS c_burden_missing
  FROM base
  GROUP BY 1
), cells AS (
  SELECT *,
  CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END AS hid,
  SUM(CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END) OVER () AS n_hidden,
  ROW_NUMBER() OVER ( ORDER BY CASE WHEN n BETWEEN 1 AND 4 THEN 1000000 ELSE n END, income_group) AS rn_small FROM cells0
), flagged AS (
  SELECT *, (hid = 1 OR (n_hidden = 1 AND rn_small = 1)) AS sup FROM cells
)
SELECT income_group,
  CASE WHEN NOT sup THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_high AS varchar) ELSE '<5' END AS n_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_high / n, 1) AS varchar) ELSE '<5' END AS pct_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_possibly_high AS varchar) ELSE '<5' END AS n_possibly_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_possibly_high / n, 1) AS varchar) ELSE '<5' END AS pct_possibly_high,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_low AS varchar) ELSE '<5' END AS n_low,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_low / n, 1) AS varchar) ELSE '<5' END AS pct_low,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(c_burden_missing AS varchar) ELSE '<5' END AS n_burden_missing,
  CASE WHEN (NOT sup AND NOT (c_high BETWEEN 1 AND 4 OR c_possibly_high BETWEEN 1 AND 4 OR c_low BETWEEN 1 AND 4 OR c_burden_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_burden_missing / n, 1) AS varchar) ELSE '<5' END AS pct_burden_missing
FROM flagged
ORDER BY income_group;
