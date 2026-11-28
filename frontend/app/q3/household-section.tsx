import { Suspense } from "react";
import { fetchQ3 } from "../../lib/q3-data";
import { DashboardStatus } from "../dashboard-ui";
import { HouseholdTable, type HouseholdColumnOptions, type HouseholdData } from "../household-table";

const score = (label: string) => ({ label: `${label} (0–1)`, decimals: 2 });
const columnOptions: HouseholdColumnOptions = {
  household_code: { label: "รหัสครัวเรือน" },
  risk_rank: { label: "อันดับ" },
  risk_quadrant: { label: "กลุ่ม", order: ["help_first", "watch", "low_heat_limited", "low_heat_coping"], values: {
    help_first: "ช่วยก่อน", watch: "เฝ้าระวัง", low_heat_limited: "ร้อนน้อย · รับมือยาก", low_heat_coping: "ร้อนน้อย · รับมือได้",
  } },
  risk_score: { label: "คะแนนเสี่ยงรวม (0–100)", decimals: 1 },
  exposure: score("เผชิญความร้อน"),
  vulnerability: score("ความเปราะบาง"),
  heat_risk: score("ผลกระทบความร้อน"),
  housing_risk: score("สภาพบ้าน"),
  lst_hh_score: score("คะแนน LST รายบ้าน"),
  finance_risk: score("การเงิน"),
  burden_risk: score("ภาระค่าไฟ"),
  coping_risk: score("ข้อจำกัดการรับมือ"),
  burden_min: { label: "ค่าไฟต่อรายได้ ต่ำสุด", percentage: true },
  burden_max: { label: "ค่าไฟต่อรายได้ สูงสุด", percentage: true },
  lst_hh_c: { label: "LST รายบ้าน (°C)", decimals: 1 },
  lst_mean_c: { label: "LST ชุมชน (°C)", decimals: 1 },
  lst_score: score("คะแนน LST ชุมชน"),
  batch_id: { label: "batch แบบสำรวจ" },
  lst_batch_id: { label: "batch LST ชุมชน" },
  lst_hh_batch_id: { label: "batch LST รายบ้าน" },
  source_row: { label: "แถวในไฟล์ดิบ" },
};
const preferred = Object.keys(columnOptions);

/** Most useful columns first; anything unexpected from the API keeps its place at the end. */
function orderColumns(columns: string[]) {
  return [...preferred.filter((key) => columns.includes(key)), ...columns.filter((key) => !preferred.includes(key))];
}

async function HouseholdResults() {
  const endpoint = process.env.Q3_API_URL;
  if (!endpoint) return <DashboardStatus>ยังไม่ได้ตั้งค่า Q3_API_URL สำหรับตารางรายครัวเรือน</DashboardStatus>;

  let data: HouseholdData;
  try {
    const payload = await fetchQ3(endpoint, true);
    if (!payload || typeof payload !== "object" ||
        !("columns" in payload) || !Array.isArray(payload.columns) ||
        !("rows" in payload) || !Array.isArray(payload.rows)) {
      throw new Error("Unexpected household response");
    }
    data = { columns: orderColumns(payload.columns), rows: payload.rows };
  } catch (error) {
    console.error("Q3 household request failed", error instanceof Error ? error.message : "Unknown error");
    return <DashboardStatus>ดึงข้อมูลรายครัวเรือนไม่สำเร็จ กรุณาตรวจสิทธิ์ AWS ของโปรไฟล์ที่กำลังใช้</DashboardStatus>;
  }
  return <HouseholdTable {...data} options={columnOptions} showRowNumbers />;
}

export function Q3HouseholdSection() {
  return (
    <section className="mt-6" aria-labelledby="q3-household-title">
      <h2 id="q3-household-title" className="mb-2 section-title">ตารางรายครัวเรือน</h2>
      <p className="mb-3 text-sm text-muted">เรียงจากความเสี่ยงสูงสุด กดหัวคอลัมน์เพื่อเปลี่ยนลำดับ</p>
      <details className="panel mb-3 px-3 py-2 text-sm">
        <summary className="cursor-pointer font-semibold">วิธีอ่านคะแนนและลำดับ</summary>
        <dl className="mt-2 space-y-2 text-muted">
          <div><dt className="font-semibold text-ink">risk_score และ risk_rank</dt><dd>คะแนนรวม 0–100 ลำดับ 1 มีคะแนนสูงสุด และคะแนนเท่ากันใช้ลำดับเดียวกัน</dd></div>
          <div><dt className="font-semibold text-ink">exposure, vulnerability และ risk_quadrant</dt><dd>สองแกนอยู่ในช่วง 0–1 บ้านที่ได้อย่างน้อย 0.5 ทั้งสองแกนอยู่ในกลุ่ม help_first หรือกลุ่มช่วยก่อน</dd></div>
          <div><dt className="font-semibold text-ink">คะแนนย่อยและช่วงค่าไฟ</dt><dd>คะแนนความร้อน สภาพบ้าน การเงิน ภาระค่าไฟ และข้อจำกัดการรับมืออยู่ในช่วง 0–1 ส่วน burden_min และ burden_max เป็นขอบล่างและขอบบนของสัดส่วนค่าไฟต่อรายได้</dd></div>
          <div><dt className="font-semibold text-ink">LST และที่มาของข้อมูล</dt><dd>lst_mean_c คืออุณหภูมิพื้นผิวระดับชุมชน และ lst_hh_c คือค่าระดับครัวเรือน หน่วย °C ช่องขีดหมายถึงไม่มีค่า คอลัมน์ batch_id และ source_row ใช้ตรวจที่มาของแถว</dd></div>
        </dl>
      </details>
      <Suspense fallback={<DashboardStatus>กำลังโหลดข้อมูลรายครัวเรือน</DashboardStatus>}>
        <HouseholdResults />
      </Suspense>
    </section>
  );
}
