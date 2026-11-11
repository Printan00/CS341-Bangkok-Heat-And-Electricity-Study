-- Q3: ครัวเรือนกลุ่มใดควรได้รับการช่วยเหลือค่าไฟก่อน และปัจจัยใดทำให้บางบ้านปรับปรุงบ้านได้ บางบ้านทำไม่ได้
-- risk_score (T13/D7) = heat/13 + housing/5 + 2 x burden_score + coping/6 (ภาระค่าไฟ x2) เทียบกับน้ำหนักเท่ากัน (risk_score_equal)
-- กลุ่มลำดับต้น = risk_rank <= 20 (อันดับเท่ากันได้อันดับเดียวกัน จึงอาจมีมากกว่า 20 บ้านตามสเปก)
-- ผลลัพธ์ไม่มีรายบ้าน; ซ่อนทุกค่าที่ 1-4 บ้าน; ผลเป็นความสัมพันธ์ ไม่ใช่เหตุและผล

-- Q3.1 จำนวนครัวเรือนที่ใช้จัดอันดับได้ และความเหมือนของลำดับต้น ระหว่างน้ำหนัก x2 กับน้ำหนักเท่ากัน
SELECT
  CASE WHEN a BETWEEN 1 AND 4 THEN '<5' ELSE CAST(a AS varchar) END AS n_usable_q3,
  CASE WHEN b BETWEEN 1 AND 4 THEN '<5' ELSE CAST(b AS varchar) END AS n_ranked,
  CASE WHEN c BETWEEN 1 AND 4 THEN '<5' ELSE CAST(c AS varchar) END AS n_not_ranked,
  CASE WHEN d BETWEEN 1 AND 4 THEN '<5' ELSE CAST(d AS varchar) END AS n_top_weighted,
  CASE WHEN e BETWEEN 1 AND 4 THEN '<5' ELSE CAST(e AS varchar) END AS n_top_equal,
  CASE WHEN f BETWEEN 1 AND 4 THEN '<5' ELSE CAST(f AS varchar) END AS n_top_both
FROM (
  SELECT
    count(*) AS a, count_if(risk_score IS NOT NULL) AS b, count_if(risk_score IS NULL) AS c,
    count_if(risk_rank <= 20) AS d, count_if(risk_rank_equal <= 20) AS e,
    count_if(risk_rank <= 20 AND risk_rank_equal <= 20) AS f
  FROM bhes.happy_home_household WHERE usable_q3
);

-- Q3.2 ลักษณะกลุ่มลำดับต้น: ชั้นรายได้
WITH base AS (
  SELECT * FROM bhes.happy_home_household WHERE usable_q3
), cells0 AS (
  SELECT CASE WHEN risk_rank IS NULL THEN '(ไม่มีอันดับ)' WHEN risk_rank <= 20 THEN 'ลำดับต้น (rank<=20)' ELSE 'ที่เหลือ' END AS risk_group, coalesce(income_ord, 0) AS income_ord,
    count(*) AS n
  FROM base
  GROUP BY 1, 2
), cells AS (
  SELECT *,
  CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END AS hid,
  SUM(CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END) OVER (PARTITION BY risk_group) AS n_hidden,
  ROW_NUMBER() OVER (PARTITION BY risk_group ORDER BY CASE WHEN n BETWEEN 1 AND 4 THEN 1000000 ELSE n END, risk_group, income_ord) AS rn_small FROM cells0
), flagged AS (
  SELECT *, (hid = 1 OR (n_hidden = 1 AND rn_small = 1)) AS sup FROM cells
)
SELECT risk_group, income_ord,
  CASE WHEN NOT sup THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN NOT sup THEN CAST(ROUND(100.0 * n / SUM(n) OVER (PARTITION BY risk_group), 1) AS varchar) ELSE '<5' END AS pct_of_group
FROM flagged
ORDER BY risk_group, income_ord;

-- Q3.3 ลักษณะกลุ่มลำดับต้น: มีแอร์
WITH base AS (
  SELECT * FROM bhes.happy_home_household WHERE usable_q3
), cells0 AS (
  SELECT CASE WHEN risk_rank IS NULL THEN '(ไม่มีอันดับ)' WHEN risk_rank <= 20 THEN 'ลำดับต้น (rank<=20)' ELSE 'ที่เหลือ' END AS risk_group, coalesce(CAST(has_aircon AS varchar), '(null)') AS has_aircon,
    count(*) AS n
  FROM base
  GROUP BY 1, 2
), cells AS (
  SELECT *,
  CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END AS hid,
  SUM(CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END) OVER (PARTITION BY risk_group) AS n_hidden,
  ROW_NUMBER() OVER (PARTITION BY risk_group ORDER BY CASE WHEN n BETWEEN 1 AND 4 THEN 1000000 ELSE n END, risk_group, has_aircon) AS rn_small FROM cells0
), flagged AS (
  SELECT *, (hid = 1 OR (n_hidden = 1 AND rn_small = 1)) AS sup FROM cells
)
SELECT risk_group, has_aircon,
  CASE WHEN NOT sup THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN NOT sup THEN CAST(ROUND(100.0 * n / SUM(n) OVER (PARTITION BY risk_group), 1) AS varchar) ELSE '<5' END AS pct_of_group
FROM flagged
ORDER BY risk_group, has_aircon;

-- Q3.4 ลักษณะกลุ่มลำดับต้น: ระดับผลกระทบความร้อน
WITH base AS (
  SELECT * FROM bhes.happy_home_household WHERE usable_q3
), cells0 AS (
  SELECT CASE WHEN risk_rank IS NULL THEN '(ไม่มีอันดับ)' WHEN risk_rank <= 20 THEN 'ลำดับต้น (rank<=20)' ELSE 'ที่เหลือ' END AS risk_group, coalesce(heat_impact_level, '(null)') AS heat_impact_level,
    count(*) AS n
  FROM base
  GROUP BY 1, 2
), cells AS (
  SELECT *,
  CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END AS hid,
  SUM(CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END) OVER (PARTITION BY risk_group) AS n_hidden,
  ROW_NUMBER() OVER (PARTITION BY risk_group ORDER BY CASE WHEN n BETWEEN 1 AND 4 THEN 1000000 ELSE n END, risk_group, heat_impact_level) AS rn_small FROM cells0
), flagged AS (
  SELECT *, (hid = 1 OR (n_hidden = 1 AND rn_small = 1)) AS sup FROM cells
)
SELECT risk_group, heat_impact_level,
  CASE WHEN NOT sup THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN NOT sup THEN CAST(ROUND(100.0 * n / SUM(n) OVER (PARTITION BY risk_group), 1) AS varchar) ELSE '<5' END AS pct_of_group
FROM flagged
ORDER BY risk_group, heat_impact_level;

-- Q3.5 ลักษณะกลุ่มลำดับต้น: เช่า/เจ้าของ (A14)
WITH base AS (
  SELECT * FROM bhes.happy_home_household WHERE usable_q3
), cells0 AS (
  SELECT CASE WHEN risk_rank IS NULL THEN '(ไม่มีอันดับ)' WHEN risk_rank <= 20 THEN 'ลำดับต้น (rank<=20)' ELSE 'ที่เหลือ' END AS risk_group, coalesce(a14_tenure_clean, '(ไม่ระบุ)') AS tenure,
    count(*) AS n
  FROM base
  GROUP BY 1, 2
), cells AS (
  SELECT *,
  CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END AS hid,
  SUM(CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END) OVER (PARTITION BY risk_group) AS n_hidden,
  ROW_NUMBER() OVER (PARTITION BY risk_group ORDER BY CASE WHEN n BETWEEN 1 AND 4 THEN 1000000 ELSE n END, risk_group, tenure) AS rn_small FROM cells0
), flagged AS (
  SELECT *, (hid = 1 OR (n_hidden = 1 AND rn_small = 1)) AS sup FROM cells
)
SELECT risk_group, tenure,
  CASE WHEN NOT sup THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN NOT sup THEN CAST(ROUND(100.0 * n / SUM(n) OVER (PARTITION BY risk_group), 1) AS varchar) ELSE '<5' END AS pct_of_group
FROM flagged
ORDER BY risk_group, tenure;

-- Q3.6 ลักษณะกลุ่มลำดับต้น: ภาระค่าไฟ
WITH base AS (
  SELECT * FROM bhes.happy_home_household WHERE usable_q3
), cells0 AS (
  SELECT CASE WHEN risk_rank IS NULL THEN '(ไม่มีอันดับ)' WHEN risk_rank <= 20 THEN 'ลำดับต้น (rank<=20)' ELSE 'ที่เหลือ' END AS risk_group, coalesce(burden_class, '(null)') AS burden_class,
    count(*) AS n
  FROM base
  GROUP BY 1, 2
), cells AS (
  SELECT *,
  CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END AS hid,
  SUM(CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END) OVER (PARTITION BY risk_group) AS n_hidden,
  ROW_NUMBER() OVER (PARTITION BY risk_group ORDER BY CASE WHEN n BETWEEN 1 AND 4 THEN 1000000 ELSE n END, risk_group, burden_class) AS rn_small FROM cells0
), flagged AS (
  SELECT *, (hid = 1 OR (n_hidden = 1 AND rn_small = 1)) AS sup FROM cells
)
SELECT risk_group, burden_class,
  CASE WHEN NOT sup THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN NOT sup THEN CAST(ROUND(100.0 * n / SUM(n) OVER (PARTITION BY risk_group), 1) AS varchar) ELSE '<5' END AS pct_of_group
FROM flagged
ORDER BY risk_group, burden_class;

-- Q3.7 ปัจจัยการปรับปรุงบ้านลดความร้อน (C2.8 เคย/ไม่เคย) x เช่า/เจ้าของ (A14)
WITH base AS (
  SELECT * FROM bhes.happy_home_household WHERE usable_q3
), cells0 AS (
  SELECT coalesce(a14_tenure_clean, '(ไม่ระบุ)') AS tenure,
    count(*) AS n,
    count_if(c2_8_heat_retrofit_clean = 'เคย') AS c_retrofit_yes,
    count_if(c2_8_heat_retrofit_clean = 'ไม่เคย') AS c_retrofit_no,
    count_if(c2_8_heat_retrofit_clean IS NULL) AS c_retrofit_missing
  FROM base
  GROUP BY 1
), cells AS (
  SELECT *,
  CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END AS hid,
  SUM(CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END) OVER () AS n_hidden,
  ROW_NUMBER() OVER ( ORDER BY CASE WHEN n BETWEEN 1 AND 4 THEN 1000000 ELSE n END, tenure) AS rn_small FROM cells0
), flagged AS (
  SELECT *, (hid = 1 OR (n_hidden = 1 AND rn_small = 1)) AS sup FROM cells
)
SELECT tenure,
  CASE WHEN NOT sup THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(c_retrofit_yes AS varchar) ELSE '<5' END AS n_retrofit_yes,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_retrofit_yes / n, 1) AS varchar) ELSE '<5' END AS pct_retrofit_yes,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(c_retrofit_no AS varchar) ELSE '<5' END AS n_retrofit_no,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_retrofit_no / n, 1) AS varchar) ELSE '<5' END AS pct_retrofit_no,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(c_retrofit_missing AS varchar) ELSE '<5' END AS n_retrofit_missing,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_retrofit_missing / n, 1) AS varchar) ELSE '<5' END AS pct_retrofit_missing
FROM flagged
ORDER BY tenure;

-- Q3.8 C2.8 x ไม่มีงบประมาณ (B12)
WITH base AS (
  SELECT * FROM bhes.happy_home_household WHERE usable_q3
), cells0 AS (
  SELECT coalesce(CAST(b12_no_budget AS varchar), '(null)') AS b12_no_budget,
    count(*) AS n,
    count_if(c2_8_heat_retrofit_clean = 'เคย') AS c_retrofit_yes,
    count_if(c2_8_heat_retrofit_clean = 'ไม่เคย') AS c_retrofit_no,
    count_if(c2_8_heat_retrofit_clean IS NULL) AS c_retrofit_missing
  FROM base
  GROUP BY 1
), cells AS (
  SELECT *,
  CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END AS hid,
  SUM(CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END) OVER () AS n_hidden,
  ROW_NUMBER() OVER ( ORDER BY CASE WHEN n BETWEEN 1 AND 4 THEN 1000000 ELSE n END, b12_no_budget) AS rn_small FROM cells0
), flagged AS (
  SELECT *, (hid = 1 OR (n_hidden = 1 AND rn_small = 1)) AS sup FROM cells
)
SELECT b12_no_budget,
  CASE WHEN NOT sup THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(c_retrofit_yes AS varchar) ELSE '<5' END AS n_retrofit_yes,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_retrofit_yes / n, 1) AS varchar) ELSE '<5' END AS pct_retrofit_yes,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(c_retrofit_no AS varchar) ELSE '<5' END AS n_retrofit_no,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_retrofit_no / n, 1) AS varchar) ELSE '<5' END AS pct_retrofit_no,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(c_retrofit_missing AS varchar) ELSE '<5' END AS n_retrofit_missing,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_retrofit_missing / n, 1) AS varchar) ELSE '<5' END AS pct_retrofit_missing
FROM flagged
ORDER BY b12_no_budget;

-- Q3.9 C2.8 x ชั้นรายได้
WITH base AS (
  SELECT * FROM bhes.happy_home_household WHERE usable_q3
), cells0 AS (
  SELECT coalesce(income_ord, 0) AS income_ord,
    count(*) AS n,
    count_if(c2_8_heat_retrofit_clean = 'เคย') AS c_retrofit_yes,
    count_if(c2_8_heat_retrofit_clean = 'ไม่เคย') AS c_retrofit_no,
    count_if(c2_8_heat_retrofit_clean IS NULL) AS c_retrofit_missing
  FROM base
  GROUP BY 1
), cells AS (
  SELECT *,
  CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END AS hid,
  SUM(CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END) OVER () AS n_hidden,
  ROW_NUMBER() OVER ( ORDER BY CASE WHEN n BETWEEN 1 AND 4 THEN 1000000 ELSE n END, income_ord) AS rn_small FROM cells0
), flagged AS (
  SELECT *, (hid = 1 OR (n_hidden = 1 AND rn_small = 1)) AS sup FROM cells
)
SELECT income_ord,
  CASE WHEN NOT sup THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(c_retrofit_yes AS varchar) ELSE '<5' END AS n_retrofit_yes,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_retrofit_yes / n, 1) AS varchar) ELSE '<5' END AS pct_retrofit_yes,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(c_retrofit_no AS varchar) ELSE '<5' END AS n_retrofit_no,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_retrofit_no / n, 1) AS varchar) ELSE '<5' END AS pct_retrofit_no,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(c_retrofit_missing AS varchar) ELSE '<5' END AS n_retrofit_missing,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_retrofit_missing / n, 1) AS varchar) ELSE '<5' END AS pct_retrofit_missing
FROM flagged
ORDER BY income_ord;

-- Q3.10 C2.8 x วัสดุ/ช่างราคาแพง (B12)
WITH base AS (
  SELECT * FROM bhes.happy_home_household WHERE usable_q3
), cells0 AS (
  SELECT coalesce(CAST(b12_costly AS varchar), '(null)') AS b12_costly,
    count(*) AS n,
    count_if(c2_8_heat_retrofit_clean = 'เคย') AS c_retrofit_yes,
    count_if(c2_8_heat_retrofit_clean = 'ไม่เคย') AS c_retrofit_no,
    count_if(c2_8_heat_retrofit_clean IS NULL) AS c_retrofit_missing
  FROM base
  GROUP BY 1
), cells AS (
  SELECT *,
  CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END AS hid,
  SUM(CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END) OVER () AS n_hidden,
  ROW_NUMBER() OVER ( ORDER BY CASE WHEN n BETWEEN 1 AND 4 THEN 1000000 ELSE n END, b12_costly) AS rn_small FROM cells0
), flagged AS (
  SELECT *, (hid = 1 OR (n_hidden = 1 AND rn_small = 1)) AS sup FROM cells
)
SELECT b12_costly,
  CASE WHEN NOT sup THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(c_retrofit_yes AS varchar) ELSE '<5' END AS n_retrofit_yes,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_retrofit_yes / n, 1) AS varchar) ELSE '<5' END AS pct_retrofit_yes,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(c_retrofit_no AS varchar) ELSE '<5' END AS n_retrofit_no,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_retrofit_no / n, 1) AS varchar) ELSE '<5' END AS pct_retrofit_no,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(c_retrofit_missing AS varchar) ELSE '<5' END AS n_retrofit_missing,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_retrofit_missing / n, 1) AS varchar) ELSE '<5' END AS pct_retrofit_missing
FROM flagged
ORDER BY b12_costly;

-- Q3.11 C2.8 x บ้านเช่า/ไม่มีสิทธิ์ตัดสินใจ (B12)
WITH base AS (
  SELECT * FROM bhes.happy_home_household WHERE usable_q3
), cells0 AS (
  SELECT coalesce(CAST(b12_renter_no_say AS varchar), '(null)') AS b12_renter_no_say,
    count(*) AS n,
    count_if(c2_8_heat_retrofit_clean = 'เคย') AS c_retrofit_yes,
    count_if(c2_8_heat_retrofit_clean = 'ไม่เคย') AS c_retrofit_no,
    count_if(c2_8_heat_retrofit_clean IS NULL) AS c_retrofit_missing
  FROM base
  GROUP BY 1
), cells AS (
  SELECT *,
  CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END AS hid,
  SUM(CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END) OVER () AS n_hidden,
  ROW_NUMBER() OVER ( ORDER BY CASE WHEN n BETWEEN 1 AND 4 THEN 1000000 ELSE n END, b12_renter_no_say) AS rn_small FROM cells0
), flagged AS (
  SELECT *, (hid = 1 OR (n_hidden = 1 AND rn_small = 1)) AS sup FROM cells
)
SELECT b12_renter_no_say,
  CASE WHEN NOT sup THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(c_retrofit_yes AS varchar) ELSE '<5' END AS n_retrofit_yes,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_retrofit_yes / n, 1) AS varchar) ELSE '<5' END AS pct_retrofit_yes,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(c_retrofit_no AS varchar) ELSE '<5' END AS n_retrofit_no,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_retrofit_no / n, 1) AS varchar) ELSE '<5' END AS pct_retrofit_no,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(c_retrofit_missing AS varchar) ELSE '<5' END AS n_retrofit_missing,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_retrofit_missing / n, 1) AS varchar) ELSE '<5' END AS pct_retrofit_missing
FROM flagged
ORDER BY b12_renter_no_say;

-- Q3.12 C2.8 x พื้นที่จำกัด (B12)
WITH base AS (
  SELECT * FROM bhes.happy_home_household WHERE usable_q3
), cells0 AS (
  SELECT coalesce(CAST(b12_limited_space AS varchar), '(null)') AS b12_limited_space,
    count(*) AS n,
    count_if(c2_8_heat_retrofit_clean = 'เคย') AS c_retrofit_yes,
    count_if(c2_8_heat_retrofit_clean = 'ไม่เคย') AS c_retrofit_no,
    count_if(c2_8_heat_retrofit_clean IS NULL) AS c_retrofit_missing
  FROM base
  GROUP BY 1
), cells AS (
  SELECT *,
  CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END AS hid,
  SUM(CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END) OVER () AS n_hidden,
  ROW_NUMBER() OVER ( ORDER BY CASE WHEN n BETWEEN 1 AND 4 THEN 1000000 ELSE n END, b12_limited_space) AS rn_small FROM cells0
), flagged AS (
  SELECT *, (hid = 1 OR (n_hidden = 1 AND rn_small = 1)) AS sup FROM cells
)
SELECT b12_limited_space,
  CASE WHEN NOT sup THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(c_retrofit_yes AS varchar) ELSE '<5' END AS n_retrofit_yes,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_retrofit_yes / n, 1) AS varchar) ELSE '<5' END AS pct_retrofit_yes,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(c_retrofit_no AS varchar) ELSE '<5' END AS n_retrofit_no,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_retrofit_no / n, 1) AS varchar) ELSE '<5' END AS pct_retrofit_no,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(c_retrofit_missing AS varchar) ELSE '<5' END AS n_retrofit_missing,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_retrofit_missing / n, 1) AS varchar) ELSE '<5' END AS pct_retrofit_missing
FROM flagged
ORDER BY b12_limited_space;

-- Q3.13 C2.8 x ไม่รู้จะปรับอย่างไร (B12)
WITH base AS (
  SELECT * FROM bhes.happy_home_household WHERE usable_q3
), cells0 AS (
  SELECT coalesce(CAST(b12_dont_know_how AS varchar), '(null)') AS b12_dont_know_how,
    count(*) AS n,
    count_if(c2_8_heat_retrofit_clean = 'เคย') AS c_retrofit_yes,
    count_if(c2_8_heat_retrofit_clean = 'ไม่เคย') AS c_retrofit_no,
    count_if(c2_8_heat_retrofit_clean IS NULL) AS c_retrofit_missing
  FROM base
  GROUP BY 1
), cells AS (
  SELECT *,
  CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END AS hid,
  SUM(CASE WHEN n BETWEEN 1 AND 4 THEN 1 ELSE 0 END) OVER () AS n_hidden,
  ROW_NUMBER() OVER ( ORDER BY CASE WHEN n BETWEEN 1 AND 4 THEN 1000000 ELSE n END, b12_dont_know_how) AS rn_small FROM cells0
), flagged AS (
  SELECT *, (hid = 1 OR (n_hidden = 1 AND rn_small = 1)) AS sup FROM cells
)
SELECT b12_dont_know_how,
  CASE WHEN NOT sup THEN CAST(n AS varchar) ELSE '<5' END AS n,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(c_retrofit_yes AS varchar) ELSE '<5' END AS n_retrofit_yes,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_retrofit_yes / n, 1) AS varchar) ELSE '<5' END AS pct_retrofit_yes,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(c_retrofit_no AS varchar) ELSE '<5' END AS n_retrofit_no,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_retrofit_no / n, 1) AS varchar) ELSE '<5' END AS pct_retrofit_no,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(c_retrofit_missing AS varchar) ELSE '<5' END AS n_retrofit_missing,
  CASE WHEN (NOT sup AND NOT (c_retrofit_yes BETWEEN 1 AND 4 OR c_retrofit_no BETWEEN 1 AND 4 OR c_retrofit_missing BETWEEN 1 AND 4)) THEN CAST(ROUND(100.0 * c_retrofit_missing / n, 1) AS varchar) ELSE '<5' END AS pct_retrofit_missing
FROM flagged
ORDER BY b12_dont_know_how;
