import type { Metadata } from "next";
import { canViewHouseholdDetails } from "../../lib/household-view";
import { getQ2Data, q2Groups, q2Percent, q2Share } from "../../lib/q2-data";
import { DashboardHeading, DashboardStatus } from "../dashboard-ui";
import { BurdenChart, CoolingByIncome } from "./figures";
import { Q2HouseholdSection } from "./household-section";
import { Q2ResultsTable } from "./results-table";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Q2 รายได้ การมีแอร์ และภาระค่าไฟ | Bangkok Heat",
  description: "ภาระค่าไฟหน้าร้อนจากแบบสำรวจ Happy Home แยกตามรายได้และการมีเครื่องปรับอากาศ",
};

export default async function Q2Page() {
  const [result, showHouseholds] = await Promise.all([getQ2Data(), canViewHouseholdDetails()]);
  const rows = result.status === "ready" ? result.rows : [];
  const income = q2Groups(rows, "income");
  const cooling = q2Groups(rows, "cooling");
  const combined = q2Groups(rows, "combined");
  const sampleSize = income.length && income.every((row) => row.households !== null)
    ? income.reduce((sum, row) => sum + (row.households ?? 0), 0) : null;
  const lower = income.find((row) => row.income === "lower");
  const upper = income.find((row) => row.income === "upper");
  const no = cooling.find((row) => row.cooling === "no");
  const yes = cooling.find((row) => row.cooling === "yes");
  const lowerShare = lower ? q2Share(lower.high, lower.households) : null;
  const upperShare = upper ? q2Share(upper.high, upper.households) : null;
  const noShare = no ? q2Share(no.high, no.households) : null;
  const yesShare = yes ? q2Share(yes.high, yes.households) : null;

  return (
    <>
      <DashboardHeading question="Q2" title="รายได้และการมีแอร์สัมพันธ์กับภาระค่าไฟอย่างไร?"
        description="เปรียบเทียบค่าไฟหน้าร้อนเทียบกับรายได้ต่อเดือน จากแบบสำรวจ Happy Home" />

      {rows.length ? (
        <div className="space-y-4">
          <nav className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm" aria-label="ส่วนของหน้า Q2">
            {sampleSize !== null && <span className="font-semibold tabular-nums">{sampleSize} ครัวเรือน</span>}
            <a className="font-semibold text-energy underline underline-offset-2" href="#q2-comparison">ผลเปรียบเทียบ</a>
            <a className="font-semibold text-energy underline underline-offset-2" href="#q2-data-tables">ตารางข้อมูลทั้งหมด</a>
            {showHouseholds && <a className="font-semibold text-energy underline underline-offset-2" href="#q2-households">ตารางรายครัวเรือน</a>}
          </nav>

          <aside className="rounded-panel bg-energy-soft p-3 text-sm compact:px-5" aria-labelledby="q2-reading-title">
            <h2 id="q2-reading-title" className="font-bold">ภาระค่าไฟ 10% คืออะไร?</h2>
            <p className="mt-1">ถ้ารายได้เดือนละ 10,000 บาท และจ่ายค่าไฟหน้าร้อน 1,000 บาท ค่าไฟคิดเป็น 10% ของรายได้ แบบสำรวจถามเป็นช่วง จึงจัดระดับจากค่าต่ำสุดและสูงสุดที่เป็นไปได้</p>
            <p className="mt-1"><strong>แดง</strong> อย่างน้อย 10% แน่นอน · <strong>ส้ม</strong> อาจถึง 10% · <strong>เขียว</strong> ต่ำกว่า 10% ตลอดช่วง · <strong>เทา</strong> ข้อมูลไม่ครบ</p>
          </aside>

          <section id="q2-comparison" className="grid scroll-mt-4 gap-3 @min-[44rem]:grid-cols-2" aria-label="ผลเปรียบเทียบภาระค่าไฟ">
            <BurdenChart id="q2-income-chart" title="รายได้กลุ่มไหนมีภาระค่าไฟสูง?" rows={income}
              guide="หนึ่งแท่งแทนบ้านทั้งหมดในช่วงรายได้ต่อเดือนนั้น (100%) ยิ่งส่วนสีแดงยาว ยิ่งมีสัดส่วนบ้านที่ภาระค่าไฟสูงมาก"
              takeaway={lower && lowerShare !== null && <>กลุ่มรายได้ไม่เกิน 10,000 บาทมี <strong>{lower.high} จาก {lower.households} บ้าน ({q2Percent(lowerShare)})</strong> ที่ภาระค่าไฟสูง{upperShare !== null && <> เทียบกับ <strong>{q2Percent(upperShare)}</strong> ในกลุ่มรายได้มากกว่า 20,000 บาท</>}</>} />
            <BurdenChart id="q2-cooling-chart" title="บ้านมีแอร์กับไม่มีแอร์ ภาระค่าไฟต่างกันแค่ไหน?" rows={cooling}
              guide="หนึ่งแท่งคือบ้านทั้งหมดในกลุ่มมีแอร์หรือไม่มีแอร์ เทียบสัดส่วนสีแดงของสองแท่ง โดยรวมทุกช่วงรายได้"
              takeaway={no && yes && noShare !== null && yesShare !== null && <>ในกลุ่มไม่มีแอร์ <strong>{no.high} จาก {no.households} บ้าน ({q2Percent(noShare)})</strong> มีภาระสูง ส่วนกลุ่มมีแอร์อยู่ที่ <strong>{yes.high} จาก {yes.households} บ้าน ({q2Percent(yesShare)})</strong> การเทียบนี้ยังไม่ได้แยกตามรายได้</>} />
            <div className="@min-[44rem]:col-span-2"><CoolingByIncome income={income} combined={combined} /></div>
            {combined.some((row) => row.high !== null) ? <div className="@min-[44rem]:col-span-2">
              <BurdenChart id="q2-combined-chart" title="ภาระค่าไฟตามการมีแอร์ภายในแต่ละช่วงรายได้" rows={combined}
                guide="เทียบส่วนสีแดงของบ้านมีแอร์และไม่มีแอร์เฉพาะคู่ที่อยู่ในช่วงรายได้เดียวกัน" />
            </div> : combined.length > 0 && <p className="text-xs text-muted @min-[44rem]:col-span-2">
              การเปรียบเทียบภาระค่าไฟระหว่างบ้านที่มีและไม่มีแอร์ภายในช่วงรายได้เดียวกันยังจำกัด เพราะต้องปกปิดผลระดับภาระในกลุ่มย่อย
            </p>}
          </section>

          <section className="panel p-4 compact:p-5" aria-labelledby="q2-method">
            <h2 id="q2-method" className="text-base font-bold">วิธีอ่านผล</h2>
            <ul className="mt-2 grid gap-2 text-sm text-muted @min-[44rem]:grid-cols-2">
              <li><strong className="text-ink">ตัวหาร</strong> ใช้จำนวนบ้านทั้งหมดในกลุ่ม รวมบ้านที่ข้อมูลค่าไฟหรือรายได้ไม่ครบ ซึ่งแสดงเป็นหมวดแยก</li>
              <li><strong className="text-ink">การมีแอร์</strong> ใช้การมีเครื่องปรับอากาศเป็นตัวแทนการเข้าถึงการทำความเย็น การประมาณผลของการใช้แอร์ต่อค่าไฟต้องใช้ข้อมูลการใช้งานและปัจจัยอื่นเพิ่ม</li>
            </ul>
          </section>

          <section id="q2-data-tables" className="scroll-mt-4 space-y-3" aria-labelledby="q2-tables-title">
            <h2 id="q2-tables-title" className="section-title">ตารางข้อมูลทั้งหมด</h2>
            <p className="text-xs text-muted">ตัวเลขแสดงจำนวนบ้านและร้อยละของบ้านทั้งหมดในแถวนั้น เลื่อนตารางด้านข้างบนจอเล็ก ขีด (—) หมายถึงปกปิดตัวเลขเพื่อคุ้มครองกลุ่มขนาดเล็กและป้องกันการคำนวณย้อนกลับ</p>
            <Q2ResultsTable id="q2-income-table" title="แยกตามรายได้ (บาท/เดือน)" rows={income} />
            <Q2ResultsTable id="q2-cooling-table" title="แยกตามการมีแอร์" rows={cooling} />
            <Q2ResultsTable id="q2-combined-table" title="แยกตามรายได้และการมีแอร์" rows={combined} />
          </section>
        </div>
      ) : (
        <DashboardStatus>
          {result.status === "unconfigured" ? "ยังไม่ได้ตั้งค่า API สำหรับข้อมูล Q2"
            : result.status === "unavailable" ? "ดึงข้อมูล Q2 จาก AWS Athena ไม่สำเร็จ กรุณาลองโหลดหน้าใหม่"
              : "ยังไม่มีข้อมูลครัวเรือนสำหรับ Q2"}
        </DashboardStatus>
      )}
      {showHouseholds && <Q2HouseholdSection />}
      <p className="mt-4 border-t border-line pt-3 text-xs text-muted">ที่มา แบบสำรวจ Happy Home · AWS Athena / <code>happy_home_risk</code></p>
    </>
  );
}
