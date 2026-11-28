import { ShieldCheck, Thermometer, Users } from "lucide-react";
import { Suspense } from "react";
import { DashboardCardTitle, DashboardDetailLink, DashboardHeading, DashboardStatus } from "./dashboard-ui";
import { getDashboardData, percent } from "../lib/dashboard-data";
import { getQ1Data, wallComparison } from "../lib/q1-data";
import { getQ3Data } from "../lib/q3-data";
import { Q3Table } from "./q3-table";

const statIcons = { sample: Users, heat: Thermometer, support: ShieldCheck };
const statTones = { sample: "bg-sand text-muted", heat: "bg-heat-soft text-heat", support: "bg-olive-soft text-olive" };

function SummaryStat({ value, label, tone }: { value: string; label: string; tone: keyof typeof statIcons }) {
  const Icon = statIcons[tone];
  return (
    <div className="panel flex min-w-0 items-center gap-2.5 p-2.5 last:col-span-2 compact:p-3.5 @min-[37rem]:last:col-span-1">
      <span className={`grid size-8 shrink-0 place-items-center rounded-full compact:size-10 ${statTones[tone]}`}><Icon className="size-4 compact:size-5" aria-hidden="true" /></span>
      <div className="flex min-w-0 flex-col">
        <dt className="mt-0.5 text-xs leading-tight text-muted compact:text-[13px]">{label}</dt>
        <dd className="-order-1 text-[clamp(20px,3.2cqi,32px)] leading-tight font-semibold tabular-nums">{value}</dd>
      </div>
    </div>
  );
}

type PreviewRow = { label: string; value: string; width: number | null };
const barColors = { heat: "bg-heat", energy: "bg-[#25877c]" };

function PreviewBars({ rows, tone }: { rows: PreviewRow[]; tone: keyof typeof barColors }) {
  return (
    <ul className="my-2 space-y-2">
      {rows.map(({ label, value, width }) => (
        <li key={label} className="grid grid-cols-[minmax(5rem,36%)_minmax(0,1fr)_3.2rem] items-center gap-2 text-xs compact:text-sm">
          <span className="leading-tight">{label}</span>
          <span className="h-2.5 rounded-full bg-sand" aria-hidden="true">
            {width !== null && <span className={`block h-full rounded-full ${barColors[tone]}`} style={{ width: `${width}%` }} />}
          </span>
          <strong className="text-right font-semibold tabular-nums">{value}</strong>
        </li>
      ))}
    </ul>
  );
}

async function OverviewResults() {
  const [q1, q2, q3] = await Promise.all([getQ1Data(), getDashboardData("all"), getQ3Data()]);
  const q1Rows = q1.status === "ready" ? q1.data.rows : [];
  const wall = wallComparison(q1Rows);
  const levels = q1Rows.filter(({ kind }) => kind === "distribution");
  const sample = levels.some(({ suppressed }) => suppressed) ? null
    : levels.reduce((total, { households }) => total + (households ?? 0), 0);
  const high = levels.find(({ label }) => label === "high");
  const highShare = sample && high?.households != null ? `${(100 * high.households / sample).toFixed(1)}%` : "—";
  const q3Rows = q3.status === "ready" ? q3.rows : [];
  const priority = q3Rows.find(({ group }) => group === "help_first");
  const income = q2.income.map((row) => {
    const value = percent(...row.count);
    return { label: row.label, value: value == null ? "—" : `${value}%`, width: value };
  });

  return (
    <>
      <dl className="grid grid-cols-2 gap-2 @min-[37rem]:grid-cols-3 @min-[37rem]:gap-3" aria-label="ตัวเลขสำคัญ">
        <SummaryStat value={sample?.toString() || "—"} label="ครัวเรือนในแบบสำรวจ Q1" tone="sample" />
        <SummaryStat value={highShare} label="ได้รับผลกระทบจากความร้อนระดับสูง" tone="heat" />
        <SummaryStat value={priority?.households?.toString() ?? "—"} label="ครัวเรือนในกลุ่มช่วยก่อน" tone="support" />
      </dl>

      <div className="mt-4 grid gap-3 @min-[44rem]:grid-cols-2">
        <article className="panel flex min-w-0 flex-col gap-2 p-4" id="heat" aria-labelledby="overview-q1">
          <DashboardCardTitle question="Q1" id="overview-q1" title="ลักษณะบ้านกับผลกระทบจากความร้อน" />
          <p className="text-xs text-muted">สัดส่วนบ้านที่ได้รับผลกระทบสูง แยกตามวัสดุผนัง</p>
          {wall ? <PreviewBars tone="heat" rows={[
            { label: "ผนังไม้", value: `${wall.wood.value.toFixed(1)}%`, width: wall.wood.value },
            { label: "ผนังวัสดุอื่น", value: `${wall.other.value.toFixed(1)}%`, width: wall.other.value },
          ]} /> : <p className="my-2 text-sm text-muted">ยังไม่มีผลเปรียบเทียบวัสดุผนังให้แสดง</p>}
          <div className="mt-auto"><DashboardDetailLink question="Q1" /></div>
        </article>

        <article className="panel flex min-w-0 flex-col gap-2 p-4" id="electricity" aria-labelledby="overview-q2">
          <DashboardCardTitle question="Q2" id="overview-q2" title="รายได้สัมพันธ์กับภาระค่าไฟอย่างไร?" />
          <p className="text-xs text-muted">ภาระค่าไฟสูงตามช่วงรายได้ (บาท/เดือน) · ข้อมูลจำลอง</p>
          <PreviewBars tone="energy" rows={income} />
          <div className="mt-auto"><DashboardDetailLink question="Q2" /></div>
        </article>

        <article className="panel min-w-0 space-y-2 p-4 @min-[44rem]:col-span-2" id="priority" aria-labelledby="overview-q3">
          <DashboardCardTitle question="Q3" id="overview-q3" title="กลุ่มไหนควรได้รับความช่วยเหลือก่อน?" />
          {q3Rows.length ? <Q3Table rows={q3Rows} labelledBy="overview-q3" /> : <p className="my-2 text-sm text-muted">ยังไม่มีผลสรุป Q3 ให้แสดง</p>}
          <DashboardDetailLink question="Q3" />
        </article>
      </div>
    </>
  );
}

export const dynamic = "force-dynamic";

export default function Home() {
  return (
    <div id="overview">
      <DashboardHeading title="ความร้อนและค่าไฟในกรุงเทพฯ"
        description="ผลการศึกษาลักษณะบ้าน ผลกระทบจากความร้อน และภาระค่าไฟ เพื่อทำความเข้าใจว่าครัวเรือนกลุ่มใดควรได้รับความช่วยเหลือก่อน" />
      <Suspense fallback={<DashboardStatus>กำลังโหลดผลสรุปจาก Athena</DashboardStatus>}>
        <OverviewResults />
      </Suspense>
    </div>
  );
}
