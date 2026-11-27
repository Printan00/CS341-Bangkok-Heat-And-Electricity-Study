import { headers } from "next/headers";
import Link from "next/link";
import { notFound } from "next/navigation";
import { fetchQ3 } from "../../../lib/q3-data";
import { HouseholdTable, type HouseholdData } from "./table";
import { DashboardHeading, DashboardStatus } from "../../dashboard-ui";

export default async function InternalQ3Page() {
  if (process.env.NODE_ENV !== "development" || process.env.Q3_INTERNAL_VIEW !== "1" || process.env.VERCEL) {
    notFound();
  }
  const host = (await headers()).get("host");
  if (!host || !/^(?:localhost|127\.0\.0\.1):\d+$/.test(host)) notFound();

  let data: HouseholdData | undefined;
  const endpoint = process.env.Q3_API_URL;
  if (endpoint) {
    try {
      const payload = await fetchQ3(endpoint, true);
      if (!payload || typeof payload !== "object" ||
          !("columns" in payload) || !Array.isArray(payload.columns) ||
          !("rows" in payload) || !Array.isArray(payload.rows)) {
        throw new Error("Unexpected household response");
      }
      data = { columns: payload.columns, rows: payload.rows };
    } catch (error) {
      console.error("Internal Q3 request failed", error instanceof Error ? error.message : "Unknown error");
    }
  }

  return (
    <>
      <DashboardHeading question="Q3" title="ตารางรายครัวเรือน"
        description="มุมมองตรวจข้อมูลภายใน · เริ่มจากลำดับความเสี่ยงสูงสุด · กดหัวคอลัมน์เพื่อเรียงข้อมูล" />
      <Link href="/q3" className="mb-3 inline-block text-sm font-medium text-heat underline">กลับไปหน้าสรุป Q3</Link>
      <details className="panel mb-3 px-3 py-2 text-sm">
        <summary className="cursor-pointer font-semibold">วิธีอ่านคะแนนและลำดับ</summary>
        <dl className="mt-2 space-y-2 text-muted">
          <div><dt className="font-semibold text-ink">risk_score และ risk_rank</dt><dd>คะแนนรวม 0–100 ลำดับ 1 มีคะแนนสูงสุด และคะแนนเท่ากันใช้ลำดับเดียวกัน</dd></div>
          <div><dt className="font-semibold text-ink">exposure, vulnerability และ risk_quadrant</dt><dd>สองแกนอยู่ในช่วง 0–1 บ้านที่ได้อย่างน้อย 0.5 ทั้งสองแกนอยู่ในกลุ่ม help_first หรือกลุ่มช่วยก่อน</dd></div>
          <div><dt className="font-semibold text-ink">คะแนนย่อยและช่วงค่าไฟ</dt><dd>คะแนนความร้อน สภาพบ้าน การเงิน ภาระค่าไฟ และข้อจำกัดการรับมืออยู่ในช่วง 0–1 ส่วน burden_min และ burden_max เป็นขอบล่างและขอบบนของสัดส่วนค่าไฟต่อรายได้</dd></div>
          <div><dt className="font-semibold text-ink">LST และที่มาของข้อมูล</dt><dd>lst_mean_c คืออุณหภูมิพื้นผิวระดับชุมชน และ lst_hh_c คือค่าระดับครัวเรือน หน่วย °C ช่องขีดหมายถึงไม่มีค่า คอลัมน์ batch_id และ source_row ใช้ตรวจที่มาของแถว</dd></div>
        </dl>
      </details>
      {data ? <HouseholdTable {...data} /> : <DashboardStatus>ดึงข้อมูล S3 ไม่สำเร็จ กรุณาตรวจสิทธิ์ AWS ของโปรไฟล์ที่กำลังใช้</DashboardStatus>}
    </>
  );
}
