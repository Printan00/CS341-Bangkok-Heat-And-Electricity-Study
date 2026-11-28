import { ArrowDown, ArrowRight } from "lucide-react";
import Image from "next/image";
import { Suspense } from "react";
import { DashboardCardTitle, DashboardDetailLink, DashboardStatus } from "./dashboard-ui";
import { getQ1Data, wallComparison } from "../lib/q1-data";
import { getQ2Data, q2Groups, q2Label, q2Percent, q2Share } from "../lib/q2-data";
import { getQ3Data } from "../lib/q3-data";
import canalIllustration from "../public/bangkok-canal-illustration.webp";
import { Q3Table } from "./q3-table";

const tones = {
  heat: { text: "text-heat", bar: "bg-heat" },
  energy: { text: "text-energy", bar: "bg-energy" },
  support: { text: "text-olive" },
};

function SummaryStat({ href, value, unit, label, detail, tone }: {
  href: string; value: string; unit?: string; label: string; detail?: string; tone: keyof typeof tones;
}) {
  return (
    <a href={href} className="group grid min-w-0 grid-cols-[6rem_minmax(0,1fr)_auto] items-center gap-x-2.5 px-1 py-3.5 hover:bg-sand/60 @min-[43rem]:grid-cols-[minmax(0,1fr)_auto] @min-[43rem]:items-end @min-[43rem]:px-5 @min-[68rem]:px-7">
      <strong className={`${tones[tone].text} text-[clamp(24px,4cqi,45px)] leading-none font-bold tabular-nums @min-[43rem]:col-span-2`}>
        {value}{unit && <span className="ms-1 text-[.5em]">{unit}</span>}
      </strong>
      <span className="min-w-0 text-sm leading-snug font-semibold @min-[43rem]:mt-1.5 compact:text-[15px]">
        {label}{detail && <span className="mt-0.5 block text-xs font-normal text-muted">{detail}</span>}
      </span>
      <ArrowRight className={`${tones[tone].text} size-4 shrink-0 motion-safe:transition-transform motion-safe:group-hover:translate-x-0.5`} aria-hidden="true" />
    </a>
  );
}

function PreviewBars({ rows, tone }: { rows: { label: string; share: number | null }[]; tone: "heat" | "energy" }) {
  return (
    <ul className="mt-3 space-y-2.5">
      {rows.map(({ label, share }) => (
        <li key={label} className="grid grid-cols-[minmax(6.25rem,34%)_minmax(0,1fr)_3.3rem] items-center gap-2.5 text-sm">
          <span className="leading-tight">{label}</span>
          <span className="h-2.5 overflow-hidden rounded-full bg-sand" aria-hidden="true">
            {share !== null && <span className={`block h-full rounded-full ${tones[tone].bar}`} style={{ width: `${share}%` }} />}
          </span>
          <strong className="text-right font-semibold tabular-nums">{q2Percent(share)}</strong>
        </li>
      ))}
    </ul>
  );
}

function OverviewHero() {
  return (
    <section className="relative isolate mt-4 overflow-hidden rounded-[14px] bg-[#f3ede2] @min-[48rem]:min-h-[254px]" aria-labelledby="overview-title">
      <div className="relative z-10 px-5 py-6 @min-[48rem]:w-[58%] @min-[48rem]:px-7 @min-[68rem]:px-8 @min-[68rem]:py-7">
        <h1 id="overview-title" className="text-[clamp(30px,4.6cqi,62px)] leading-[1.04] font-bold tracking-[-.025em]">
          ความร้อนและค่าไฟ<br />ในกรุงเทพฯ
        </h1>
        <div className="mt-3 h-0.5 w-[3.5rem] bg-heat @min-[48rem]:mt-4" aria-hidden="true" />
        <p className="mt-2 max-w-lg text-sm text-ink/85 @min-[68rem]:text-[17px]">ผลสำรวจ Happy Home จาก 2 ชุมชนริม<span className="whitespace-nowrap">คลองเปรมประชากร</span></p>
        <a href="#findings" className="mt-3 inline-flex min-h-10 items-center gap-2 rounded-lg bg-ink px-4 text-sm font-semibold text-white hover:bg-[#3c342b]">
          ดูผลสำรวจ <ArrowDown size={15} aria-hidden="true" />
        </a>
      </div>
      <figure className="relative h-32 @min-[31rem]:h-40 @min-[48rem]:absolute @min-[48rem]:inset-y-0 @min-[48rem]:right-0 @min-[48rem]:h-full @min-[48rem]:w-[55%] @min-[48rem]:[clip-path:polygon(13%_0,100%_0,100%_100%,0_100%)]">
        <Image src={canalIllustration} alt="ภาพวาดบ้านริมคลองกับจระเข้ตัวเล็กที่กำลังว่ายน้ำ" fill preload sizes="(max-width: 815px) 100vw, (max-width: 1536px) 52vw, 720px" className="object-cover object-[50%_88%] @min-[48rem]:object-[50%_57%]" />
        <figcaption className="absolute bottom-2 left-2.5 rounded-sm bg-ink/80 px-1.5 py-0.5 text-[10px] text-white @min-[48rem]:right-2.5 @min-[48rem]:left-auto">ภาพประกอบ</figcaption>
      </figure>
    </section>
  );
}

async function OverviewResults() {
  const [q1, q2, q3] = await Promise.all([getQ1Data(), getQ2Data(), getQ3Data()]);
  const q1Rows = q1.status === "ready" ? q1.data.rows : [];
  const wall = wallComparison(q1Rows);
  const levels = q1Rows.filter(({ kind }) => kind === "distribution");
  const sample = levels.some(({ suppressed }) => suppressed) ? null
    : levels.reduce((total, { households }) => total + (households ?? 0), 0);
  const high = levels.find(({ label }) => label === "high")?.households;
  const highShare = q2Share(high ?? null, sample);

  const q2Rows = q2.status === "ready" ? q2.rows : [];
  const income = q2Groups(q2Rows, "income");
  const lower = income.find(({ income }) => income === "lower");
  const lowIncomeShare = lower ? q2Share(lower.high, lower.households) : null;
  const cooling = q2Groups(q2Rows, "cooling");
  const noAircon = cooling.find(({ cooling }) => cooling === "no");
  const aircon = cooling.find(({ cooling }) => cooling === "yes");
  const noAirconShare = noAircon ? q2Share(noAircon.high, noAircon.households) : null;
  const airconShare = aircon ? q2Share(aircon.high, aircon.households) : null;

  const q3Rows = q3.status === "ready" ? q3.rows : [];
  const priorityCount = q3Rows.find(({ group }) => group === "help_first")?.households ?? null;

  return (
    <>
      <nav className="my-3 grid divide-y divide-line border-b border-line pb-1 @min-[43rem]:my-4 @min-[43rem]:grid-cols-3 @min-[43rem]:divide-x @min-[43rem]:divide-y-0 @min-[43rem]:pb-3" aria-label="ตัวเลขสำคัญ">
        <SummaryStat href="#heat" tone="heat" value={q2Percent(highShare)}
          label="ได้รับผลกระทบจากความร้อนสูง" detail={highShare !== null ? `${high} จาก ${sample} บ้านในผล Q1` : undefined} />
        <SummaryStat href="#electricity" tone="energy" value={q2Percent(lowIncomeShare)}
          label="ภาระค่าไฟสูงในกลุ่มรายได้ไม่เกิน 10,000 บาท" detail={lowIncomeShare !== null ? `${lower?.high} จาก ${lower?.households} บ้านในกลุ่มนี้` : undefined} />
        <SummaryStat href="#priority" tone="support" value={priorityCount?.toString() ?? "—"}
          unit={priorityCount === null ? undefined : "บ้าน"} label="อยู่ในกลุ่มที่ควรช่วยก่อน" detail="ตามเกณฑ์ความร้อนและความเปราะบาง" />
      </nav>

      <section aria-labelledby="findings">
        <h2 id="findings" className="text-[clamp(22px,3.4cqi,34px)] leading-tight font-bold">ผลสำรวจที่สำคัญ</h2>
        <div className="mt-3 grid gap-3 @min-[48rem]:grid-cols-2 @min-[68rem]:gap-4">
          <article className="panel flex min-w-0 flex-col p-4 @min-[68rem]:p-5" id="heat" aria-labelledby="overview-q1">
            <DashboardCardTitle question="Q1" id="overview-q1" title="ผนังบ้านกับผลกระทบจากความร้อน" />
            <p className="mt-1.5 text-xs text-muted">สัดส่วนบ้านที่ได้รับผลกระทบสูง แยกตามวัสดุผนัง</p>
            {wall ? <PreviewBars tone="heat" rows={[
              { label: "ผนังไม้", share: wall.wood.value },
              { label: "ผนังวัสดุอื่น", share: wall.other.value },
            ]} /> : <p className="my-2 text-sm text-muted">ยังไม่มีผลเปรียบเทียบวัสดุผนังให้แสดง</p>}
            {wall && wall.wood.value > wall.other.value && <p className="mt-3 text-sm text-muted">ในกลุ่มสำรวจ บ้านผนังไม้มีสัดส่วนผลกระทบสูงกว่าบ้านผนังวัสดุอื่น</p>}
            <div className="mt-auto pt-3"><div className="border-t border-line pt-1"><DashboardDetailLink question="Q1" /></div></div>
          </article>

          <article className="panel flex min-w-0 flex-col p-4 @min-[68rem]:p-5" id="electricity" aria-labelledby="overview-q2">
            <DashboardCardTitle question="Q2" id="overview-q2" title="รายได้กับภาระค่าไฟ" />
            <p className="mt-1.5 text-xs text-muted">สัดส่วนบ้านที่มีภาระค่าไฟสูง แยกตามรายได้ต่อเดือน (บาท)</p>
            {income.length ? <PreviewBars tone="energy" rows={income.map((row) => ({
              label: q2Label(row), share: q2Share(row.high, row.households),
            }))} /> : <p className="my-2 text-sm text-muted">ยังไม่มีผล Q2 จาก AWS ให้แสดง</p>}
            {noAirconShare !== null && airconShare !== null && (
              <p className="mt-3 text-sm text-muted">เมื่อรวมทุกช่วงรายได้ ภาระสูงพบในบ้านไม่มีแอร์ <strong className="text-ink">{q2Percent(noAirconShare)}</strong> และบ้านมีแอร์ <strong className="text-ink">{q2Percent(airconShare)}</strong></p>
            )}
            <div className="mt-auto pt-3"><div className="border-t border-line pt-1"><DashboardDetailLink question="Q2" /></div></div>
          </article>

          <article className="panel min-w-0 space-y-2.5 p-4 @min-[48rem]:col-span-2 @min-[68rem]:p-5" id="priority" aria-labelledby="overview-q3">
            <DashboardCardTitle question="Q3" id="overview-q3" title="กลุ่มครัวเรือนที่ควรช่วยก่อน" />
            <p className="text-sm text-muted">จัดกลุ่มจากระดับการเผชิญความร้อนและความเปราะบางของครัวเรือน</p>
            {q3Rows.length ? <Q3Table rows={q3Rows} labelledBy="overview-q3" appearance="overview" /> : <p className="my-2 text-sm text-muted">ยังไม่มีผลสรุป Q3 ให้แสดง</p>}
            <DashboardDetailLink question="Q3" />
          </article>
        </div>
      </section>
    </>
  );
}

export const dynamic = "force-dynamic";

export default function Home() {
  return (
    <div id="overview">
      <OverviewHero />
      <Suspense fallback={<div className="mt-4"><DashboardStatus>กำลังโหลดผลสรุปจาก Athena</DashboardStatus></div>}>
        <OverviewResults />
      </Suspense>
    </div>
  );
}
