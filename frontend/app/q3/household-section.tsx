import { Suspense } from "react";
import { canViewHouseholdDetails } from "../../lib/household-view";
import { fetchQ3 } from "../../lib/q3-data";
import { DashboardStatus } from "../dashboard-ui";
import { HouseholdTable, type HouseholdData } from "../household-table";

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
    data = { columns: payload.columns, rows: payload.rows };
  } catch (error) {
    console.error("Q3 household request failed", error instanceof Error ? error.message : "Unknown error");
    return <DashboardStatus>ดึงข้อมูลรายครัวเรือนไม่สำเร็จ กรุณาตรวจสิทธิ์ AWS ของโปรไฟล์ที่กำลังใช้</DashboardStatus>;
  }
  return <HouseholdTable {...data} />;
}

export async function Q3HouseholdSection() {
  if (!await canViewHouseholdDetails()) return null;

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
