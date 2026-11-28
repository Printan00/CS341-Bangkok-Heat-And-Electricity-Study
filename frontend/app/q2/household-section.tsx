import { Suspense } from "react";
import { fetchDashboardApi } from "../../lib/dashboard-api";
import { q2Endpoint } from "../../lib/q2-data";
import { DashboardStatus } from "../dashboard-ui";
import { HouseholdTable, type HouseholdCell, type HouseholdColumnOptions, type HouseholdData } from "../household-table";

const columnOptions: HouseholdColumnOptions = {
  household_code: { label: "รหัสครัวเรือน" },
  income_group: { label: "รายได้ (บาท/เดือน)", values: {
    "1) ไม่เกิน 10,000": "ไม่เกิน 10,000",
    "2) 10,001-20,000": "10,001–20,000",
    "3) มากกว่า 20,000": "มากกว่า 20,000",
  } },
  has_aircon: { label: "การมีแอร์", values: { true: "มีแอร์", false: "ไม่มีแอร์" } },
  burden_class: { label: "ระดับภาระค่าไฟ", order: ["low", "possibly_high", "high"],
    values: { low: "ต่ำ", possibly_high: "อาจสูง", high: "สูงแน่นอน" } },
  burden_min: { label: "ค่าไฟต่อรายได้ ต่ำสุด", percentage: true },
  burden_max: { label: "ค่าไฟต่อรายได้ สูงสุด", percentage: true },
  burden_risk: { label: "คะแนนภาระค่าไฟ" },
  finance_risk: { label: "คะแนนความเสี่ยงการเงิน" },
  coping_risk: { label: "คะแนนข้อจำกัดการรับมือ" },
  exposure: { label: "คะแนนเผชิญความร้อน" },
  vulnerability: { label: "คะแนนความเปราะบาง" },
  risk_score: { label: "คะแนนเสี่ยงรวม" },
  risk_rank: { label: "อันดับความเสี่ยง" },
};

const columns = Object.keys(columnOptions);

function parseHouseholds(payload: unknown): HouseholdData {
  if (!payload || typeof payload !== "object" || !("rows" in payload) || !Array.isArray(payload.rows)) {
    throw new Error("Unexpected Q2 household response");
  }
  const seen = new Set<string>();
  const rows = payload.rows.map((entry: unknown) => {
    if (!entry || typeof entry !== "object" || !("household_code" in entry) ||
        typeof entry.household_code !== "string" || !entry.household_code || seen.has(entry.household_code)) {
      throw new Error("Invalid Q2 household code");
    }
    seen.add(entry.household_code);
    const source = entry as Record<string, unknown>;
    const row: Record<string, HouseholdCell> = {};
    for (const key of columns) {
      const value = source[key];
      if (value === null || typeof value === "string" || typeof value === "boolean" ||
          (typeof value === "number" && Number.isFinite(value))) {
        row[key] = value;
      } else {
        throw new Error("Invalid Q2 household field");
      }
    }
    return row;
  });
  return { columns, rows };
}

async function HouseholdResults() {
  const endpoint = q2Endpoint();
  if (!endpoint) return <DashboardStatus>ยังไม่ได้ตั้งค่า API สำหรับตารางรายครัวเรือน Q2</DashboardStatus>;

  let data: HouseholdData;
  try {
    const url = new URL(endpoint);
    url.pathname = `${url.pathname.replace(/\/$/, "")}/households`;
    data = parseHouseholds(await fetchDashboardApi(url.href));
  } catch (error) {
    console.error("Q2 household request failed", error instanceof Error ? error.message : "Unknown error");
    return <DashboardStatus>ดึงข้อมูลรายครัวเรือนไม่สำเร็จ กรุณาตรวจสิทธิ์ AWS ของโปรไฟล์ที่กำลังใช้</DashboardStatus>;
  }
  return data.rows.length ? <HouseholdTable {...data} options={columnOptions} showRowNumbers />
    : <DashboardStatus>ยังไม่มีข้อมูลรายครัวเรือนสำหรับ Q2</DashboardStatus>;
}

export function Q2HouseholdSection() {
  return (
    <section id="q2-households" className="mt-6 scroll-mt-4" aria-labelledby="q2-households-title">
      <h2 id="q2-households-title" className="mb-2 section-title">ตารางรายครัวเรือน Q2</h2>
      <p className="mb-3 text-sm text-muted">หนึ่งแถวต่อหนึ่งครัวเรือน เริ่มจากอันดับความเสี่ยงสูงสุด กดหัวคอลัมน์เพื่อเรียงข้อมูล และเลื่อนด้านข้างเพื่อดูคอลัมน์ที่เหลือ</p>
      <Suspense fallback={<DashboardStatus>กำลังโหลดข้อมูลรายครัวเรือนจาก S3</DashboardStatus>}>
        <HouseholdResults />
      </Suspense>
    </section>
  );
}
