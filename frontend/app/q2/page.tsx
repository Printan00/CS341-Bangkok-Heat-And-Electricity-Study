import type { Metadata } from "next";
import { ElectricityChart } from "../charts";
import { CommunityFilter } from "../controls";
import { DashboardHeading } from "../dashboard-ui";
import { getDashboardData, parseCommunity } from "../../lib/dashboard-data";

export const metadata: Metadata = {
  title: "Q2 รายได้และภาระค่าไฟ | Bangkok Heat",
};

export default async function Q2Page({ searchParams }: { searchParams: Promise<{ community?: string | string[] }> }) {
  const community = parseCommunity((await searchParams).community);
  const data = await getDashboardData(community);

  return (
    <>
      <DashboardHeading question="Q2" title="รายได้สัมพันธ์กับภาระค่าไฟอย่างไร?"
        description="ดูสัดส่วนครัวเรือนที่จ่ายค่าไฟหน้าร้อนอย่างน้อย 10% ของรายได้ต่อเดือน · ข้อมูลจำลอง" />
      <section className="panel mb-3 flex flex-wrap items-center justify-between gap-3 p-4" aria-label="ภาพรวมและตัวกรอง Q2">
        <dl className="flex flex-wrap gap-x-6 gap-y-2">
          <div><dt className="text-xs text-muted">ครัวเรือนในชุดจำลอง</dt><dd className="text-xl font-semibold tabular-nums">{data.sampleSize}</dd></div>
          <div><dt className="text-xs text-muted">มีภาระค่าไฟสูงในชุดจำลอง</dt><dd className="text-xl font-semibold text-energy tabular-nums">{data.burdenPercent == null ? "—" : `${data.burdenPercent}%`}</dd></div>
        </dl>
        <CommunityFilter community={community} />
      </section>
      <ElectricityChart rows={data.income} />
    </>
  );
}
