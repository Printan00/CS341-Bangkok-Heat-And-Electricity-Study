-- คุณภาพข้อมูลของตารางที่ใช้ตอบ Q1-Q3 (จำนวนแถว, ค่าสูญหายรายตัวแปรหลัก, ธง dq) ไม่มีรหัสครัวเรือนในผลลัพธ์
SELECT 'rows' AS item, CAST(count(*) AS varchar) AS value FROM bhes.happy_home_household
UNION ALL SELECT 'usable_q1', CAST(count_if(usable_q1) AS varchar) FROM bhes.happy_home_household
UNION ALL SELECT 'usable_q2', CAST(count_if(usable_q2) AS varchar) FROM bhes.happy_home_household
UNION ALL SELECT 'usable_q3', CAST(count_if(usable_q3) AS varchar) FROM bhes.happy_home_household
UNION ALL SELECT 'community unknown', CASE WHEN count_if(community_key = 'unknown') BETWEEN 1 AND 4 THEN '<5' ELSE CAST(count_if(community_key = 'unknown') AS varchar) END FROM bhes.happy_home_household
UNION ALL SELECT 'null ' || v, CASE WHEN c BETWEEN 1 AND 4 THEN '<5' ELSE CAST(c AS varchar) END FROM (
  SELECT 'income_ord' AS v, count_if(income_ord IS NULL) AS c FROM bhes.happy_home_household
  UNION ALL SELECT 'bill_summer_ord', count_if(bill_summer_ord IS NULL) FROM bhes.happy_home_household
  UNION ALL SELECT 'burden_class', count_if(burden_class IS NULL) FROM bhes.happy_home_household
  UNION ALL SELECT 'has_aircon', count_if(has_aircon IS NULL) FROM bhes.happy_home_household
  UNION ALL SELECT 'housing_heat_score', count_if(housing_heat_score IS NULL) FROM bhes.happy_home_household
  UNION ALL SELECT 'heat_impact_score', count_if(heat_impact_score IS NULL) FROM bhes.happy_home_household
  UNION ALL SELECT 'coping_limit_score', count_if(coping_limit_score IS NULL) FROM bhes.happy_home_household
  UNION ALL SELECT 'risk_score', count_if(risk_score IS NULL) FROM bhes.happy_home_household
  UNION ALL SELECT 'c2_8_heat_retrofit_clean', count_if(c2_8_heat_retrofit_clean IS NULL) FROM bhes.happy_home_household
  UNION ALL SELECT 'a14_tenure_clean', count_if(a14_tenure_clean IS NULL) FROM bhes.happy_home_household
)
UNION ALL SELECT 'dq_flags empty', CASE WHEN count_if(dq_flags = '') BETWEEN 1 AND 4 THEN '<5' ELSE CAST(count_if(dq_flags = '') AS varchar) END FROM bhes.happy_home_household;
