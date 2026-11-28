import type { Metadata } from "next";
import { getQ1Data, wallComparison } from "../../lib/q1-data";
import { DashboardHeading, DashboardStatus } from "../dashboard-ui";
import { FeatureComparison } from "./comparison";
import { HousingScore, ImpactDistribution, WallHeatmap } from "./figures";
import { HouseholdContext } from "./context";
import { HousingExplorer } from "./explore";
import { Q1Method } from "./method";
import { Q1ResultsTable } from "./results-table";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Q1 ลักษณะบ้านกับผลกระทบจากความร้อน | Bangkok Heat",
  description: "ผลวิเคราะห์ระดับกลุ่มจากแบบสำรวจ Happy Home",
};

export default async function Q1Page() {
  const result = await getQ1Data();
  const data = result.status === "ready" ? result.data : undefined;
  const wall = wallComparison(data?.rows ?? []);
  const wood = wall?.wood;
  const other = wall?.other;

  return (
    <>
      <DashboardHeading question="Q1" title="ลักษณะบ้านกับผลกระทบจากความร้อน"
        description="เปรียบเทียบครัวเรือนในแบบสำรวจ Happy Home ที่มีข้อมูลครบสำหรับคำถาม Q1" />

      {data?.rows.length ? (
        <>
          <nav className="flex flex-wrap gap-x-4 gap-y-1 text-xs font-semibold text-heat" aria-label="ส่วนของหน้า Q1">
            <a className="underline-offset-2 hover:underline" href="#q1-summary">ผลหลัก</a>
            <a className="underline-offset-2 hover:underline" href="#q1-detail">รายละเอียดลักษณะบ้าน</a>
            <a className="underline-offset-2 hover:underline" href="#q1-context">บริบทครัวเรือน</a>
            <a className="underline-offset-2 hover:underline" href="#q1-table">ตารางข้อมูลทั้งหมด</a>
            <a className="underline-offset-2 hover:underline" href="#q1-method">วิธีคำนวณ</a>
          </nav>
          {wood?.value != null && other?.value != null && (
            <aside className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 rounded-panel bg-heat-soft px-3 py-3 compact:px-5" aria-label="ผลเปรียบเทียบวัสดุผนัง">
              <strong className="text-[clamp(32px,5vw,54px)] leading-none font-bold tracking-[-.04em] text-heat tabular-nums">{wood.value.toFixed(1)}%</strong>
              <div className="compact:border-l compact:border-heat/25 compact:pl-5">
                <h2 className="text-base font-bold text-heat compact:text-xl">{wood.value > other.value ? "บ้านผนังไม้มีสัดส่วนผลกระทบสูงมากกว่า" : wood.value < other.value ? "บ้านผนังวัสดุอื่นมีสัดส่วนผลกระทบสูงมากกว่า" : "ทั้งสองกลุ่มมีสัดส่วนผลกระทบสูงเท่ากัน"}</h2>
                <p className="text-sm text-muted">ผนังไม้ {wood.high}/{wood.households} บ้าน เทียบกับผนังวัสดุอื่น {other.value.toFixed(1)}% ({other.high}/{other.households} บ้าน)</p>
              </div>
            </aside>
          )}
          <div id="q1-summary" className="mt-4 grid gap-3 @min-[44rem]:grid-cols-[1.06fr_1fr]">
            <FeatureComparison {...data} />
            <WallHeatmap rows={data.rows} />
            <HousingScore rows={data.rows} />
            <ImpactDistribution rows={data.rows} />
          </div>
          <HousingExplorer rows={data.rows} />
          <HouseholdContext rows={data.rows} />
          <Q1ResultsTable rows={data.rows} />
        </>
      ) : (
        <DashboardStatus>
          {result.status === "unconfigured" ? "ยังไม่ได้ตั้งค่า API สำหรับข้อมูล Q1"
            : result.status === "unavailable" ? "ดึงข้อมูล Q1 จาก Athena ไม่สำเร็จ กรุณาลองโหลดหน้าใหม่"
              : "ยังไม่มีครัวเรือนที่มีข้อมูลครบสำหรับ Q1"}
        </DashboardStatus>
      )}

      <Q1Method />

      <div className="mt-4 grid gap-1.5 border-t border-line pt-3 text-xs text-muted @min-[44rem]:grid-cols-2">
        <p><strong className="text-ink">ที่มา</strong> แบบสำรวจ Happy Home · ข้อมูลสรุปจาก Athena</p>
        <p><strong className="text-ink">การตีความ</strong> แบบสำรวจรายงานผลย้อนหลัง ผลแสดงความสัมพันธ์ในกลุ่มตัวอย่าง และปกปิดค่าที่อาจเผยจำนวนกลุ่มเล็ก</p>
      </div>
    </>
  );
}
