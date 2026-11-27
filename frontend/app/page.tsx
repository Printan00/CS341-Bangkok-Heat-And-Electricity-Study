import { Info, Thermometer, Users, Zap, type LucideIcon } from "lucide-react";
import { ElectricityChart, HousingChart } from "./charts";
import { CommunityFilter, Methodology, SectionNavigation } from "./controls";
import { Q3Section } from "./q3-section";
import { getDashboardData, parseCommunity, type DashboardData } from "../lib/dashboard-data";

type SearchParams = Promise<{ community?: string | string[] }>;

const statTones = {
  sample: "bg-[#f5ecd9] text-[#8a5a23]",
  heat: "bg-heat-soft text-heat",
  energy: "bg-energy-soft text-energy",
};

function Summary({ data }: { data: DashboardData }) {
  const stats: {
    value: number | string;
    label: string;
    detail?: string;
    tone: keyof typeof statTones;
    icon: LucideIcon;
  }[] = [
    { value: data.sampleSize, label: "ครัวเรือนในกลุ่มตัวอย่าง", tone: "sample", icon: Users },
    { value: data.heatPercent === null ? "—" : `${data.heatPercent}%`, label: "ได้รับผลกระทบสูงจากความร้อน", tone: "heat", icon: Thermometer },
    { value: data.burdenPercent === null ? "—" : `${data.burdenPercent}%`, label: "มีภาระค่าไฟสูง", detail: "ค่าไฟ ≥ 10% ของรายได้", tone: "energy", icon: Zap },
  ];

  return (
    <dl className="grid grid-cols-2 gap-2 @min-[36rem]:grid-cols-3 @min-[36rem]:gap-2.5" aria-label="ตัวเลขสำคัญ">
      {stats.map(({ label, value, detail, tone, icon: Icon }) => (
        <div className="panel stat" key={label}>
          <dt className="text-[13px] leading-[1.35] font-medium text-muted">
            {label}{detail && <small className="block text-xs font-normal">{detail}</small>}
          </dt>
          <dd className="-order-1 w-fit text-[clamp(24px,3.1cqi,32px)] leading-[1.1] font-semibold tracking-[-.035em] tabular-nums">{value}</dd>
          <span className={`stat-icon ${statTones[tone]}`} aria-hidden="true">
            <Icon strokeWidth={1.8} className="size-[17px]" />
          </span>
        </div>
      ))}
    </dl>
  );
}

export default async function Home({ searchParams }: { searchParams: SearchParams }) {
  const community = parseCommunity((await searchParams).community);
  const data = await getDashboardData(community);

  return (
    <div className="min-h-screen desktop:grid desktop:grid-cols-[174px_minmax(0,1fr)] wide:grid-cols-[192px_minmax(0,1fr)]">
      <a className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-10 focus:rounded-lg focus:bg-white focus:px-3.5 focus:py-2" href="#overview">ข้ามไปยังเนื้อหา</a>
      <aside className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2 border-b border-line bg-white px-3 pt-2.5 pb-2 compact:px-5 desktop:sticky desktop:top-0 desktop:flex desktop:h-dvh desktop:flex-col desktop:items-stretch desktop:gap-4 desktop:self-start desktop:overflow-y-auto desktop:border-r desktop:border-b-0 desktop:px-3 desktop:pt-4 desktop:pb-3 wide:px-4">
        <a href="#overview" lang="en" className="flex min-h-9 flex-col justify-center whitespace-nowrap desktop:border-b desktop:border-line desktop:px-2 desktop:pb-3">
          <strong className="text-base leading-[1.2] font-bold tracking-[-.035em]">Bangkok Heat</strong>
          <small className="mt-1 text-[9px] font-semibold tracking-[.13em] text-muted uppercase">Electricity Study</small>
        </a>
        <div className="col-span-full">
          <p className="mx-2 mb-1 hidden text-[13px] font-semibold text-muted desktop:block">งานวิจัย</p>
          <SectionNavigation />
        </div>
        <span className="col-start-2 row-start-1 flex items-center gap-2 rounded-[9px] border border-[#ece7dc] bg-sand px-2 py-[5px] text-[13px] whitespace-nowrap text-muted desktop:mt-auto desktop:px-[11px] desktop:py-[9px]"><Info size={17} aria-hidden="true" /> Q1–Q2 ข้อมูลจำลอง</span>
      </aside>

      <main className="min-w-0" id="overview" tabIndex={-1}>
        <div className="@container mx-auto max-w-[1184px] px-3 compact:px-5 wide:px-6">
          <header className="flex min-h-11 items-center justify-between gap-2 border-b border-line text-[13px] text-muted compact:min-h-12">
            <p>แดชบอร์ด <span aria-hidden="true" className="px-1.5">/</span> <strong className="font-semibold text-ink">ภาพรวม</strong></p>
            <Methodology />
          </header>
          <div className="py-3.5 compact:py-4">
            <h1 className="text-[clamp(24px,3.65cqi,36px)] leading-[1.2] font-bold text-pretty">ความร้อนและค่าไฟในกรุงเทพฯ</h1>
            <p className="mt-1 text-sm text-muted">สำรวจว่าบ้านแบบไหนได้รับผลกระทบจากความร้อน ใครแบกภาระค่าไฟสูง และกลุ่มใดควรได้รับความช่วยเหลือก่อน</p>
          </div>
          <Summary data={data} />
          <section className="mt-4" aria-labelledby="comparison-title">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-x-3 gap-y-1.5">
              <div>
                <h2 id="comparison-title" className="section-title">ความร้อนและภาระค่าไฟ</h2>
                <p className="mt-0.5 text-[13px] text-muted">เปรียบเทียบตามลักษณะบ้านและรายได้</p>
              </div>
              <CommunityFilter community={community} />
            </div>
            <div className="grid gap-2.5 @min-[42rem]:grid-cols-2">
              <HousingChart rows={data.housing} />
              <ElectricityChart rows={data.income} />
            </div>
          </section>
          <Q3Section />
          <footer className="mt-3 flex flex-wrap justify-between gap-x-4 gap-y-1 border-t border-line pt-2 pb-3 text-xs text-muted"><span>Bangkok Heat and Electricity Study</span><span>Q1–Q2 ใช้ข้อมูลจำลอง</span></footer>
        </div>
      </main>
    </div>
  );
}
