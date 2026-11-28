import type { ReactNode } from "react";
import { burdenKeys, q2Label, q2Percent, q2Share, type Q2Row } from "../../lib/q2-data";

export const burdenLabels = { high: "สูง", possibly_high: "อาจสูง", low: "ต่ำ", missing: "ข้อมูลไม่ครบ" };
const burdenColors = { high: "bg-[#a33e25]", possibly_high: "bg-[#dba04d]", low: "bg-[#25877c]", missing: "bg-[#b5afa4]" };

function Axis() {
  return <div className="mt-1 flex justify-between text-[11px] text-muted tabular-nums" aria-hidden="true">
    {[0, 25, 50, 75, 100].map((value) => <span key={value}>{value}%</span>)}
  </div>;
}

export function BurdenChart({ id, title, rows, guide, takeaway }: {
  id: string; title: string; rows: Q2Row[]; guide: string; takeaway?: ReactNode;
}) {
  return (
    <figure className="panel min-w-0 p-4 compact:p-5" aria-labelledby={id}>
      <figcaption id={id} className="text-base font-bold">{title}</figcaption>
      <p className="mt-1 text-sm text-muted">{guide}</p>
      <ul className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted" aria-label="ระดับภาระค่าไฟ">
        {burdenKeys.map((key) => <li className="flex items-center gap-1.5" key={key}>
          <span className={`size-2.5 rounded-sm ${burdenColors[key]}`} aria-hidden="true" />{burdenLabels[key]}
        </li>)}
      </ul>
      <ul className="mt-4 space-y-4">
        {rows.map((row) => (
          <li key={q2Label(row)}>
            <div className="mb-1 flex flex-wrap items-center justify-between gap-x-2 text-sm">
              <span className="font-semibold">{q2Label(row)}</span>
              <span className="text-xs text-muted">{row.households == null ? "ปกปิดจำนวนบ้าน" : `${row.households} บ้าน`}</span>
            </div>
            {row.high == null ? <p className="rounded-md bg-sand px-2 py-1 text-xs text-muted">ปกปิดสัดส่วน</p> : (
              <>
                <div className="flex h-3 overflow-hidden rounded-full bg-sand" aria-hidden="true">
                  {burdenKeys.map((key) => <span key={key} className={burdenColors[key]} style={{ width: `${q2Share(row[key], row.households)}%` }} />)}
                </div>
                <p className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-muted tabular-nums">
                  {burdenKeys.filter((key) => key !== "missing" || row.missing).map((key) => (
                    <span key={key} className={key === "high" ? "font-semibold text-heat" : ""}>{burdenLabels[key]} {q2Percent(q2Share(row[key], row.households))}</span>
                  ))}
                </p>
              </>
            )}
          </li>
        ))}
      </ul>
      {takeaway && <p className="mt-4 rounded-md bg-sand px-3 py-2 text-sm">{takeaway}</p>}
    </figure>
  );
}

export function CoolingByIncome({ income, combined }: { income: Q2Row[]; combined: Q2Row[] }) {
  return (
    <figure className="panel min-w-0 p-4 compact:p-5" aria-labelledby="q2-cooling-mix">
      <figcaption id="q2-cooling-mix" className="text-base font-bold">แต่ละช่วงรายได้มีแอร์มากน้อยแค่ไหน</figcaption>
      <p className="mt-1 text-sm text-muted">ส่วนสีเขียวคือบ้านที่มีแอร์ เทียบกับบ้านทั้งหมดในช่วงรายได้นั้นที่ตอบเรื่องแอร์ ยิ่งแท่งสีเขียวยาว ยิ่งมีบ้านที่มีแอร์เป็นสัดส่วนมาก</p>
      <ul className="mt-4 space-y-3">
        {income.map((group) => {
          const rows = combined.filter((row) => row.income === group.income);
          const no = rows.find((row) => row.cooling === "no");
          const yes = rows.find((row) => row.cooling === "yes");
          const hidden = no?.households === null || yes?.households === null;
          const total = (yes?.households ?? 0) + (no?.households ?? 0);
          const share = hidden ? null : q2Share(yes?.households ?? 0, total);
          return (
            <li key={group.income}>
              <div className="mb-1 flex flex-wrap justify-between gap-x-2 text-sm">
                <span className="font-semibold">{q2Label(group)}</span>
                <span className="text-xs text-muted tabular-nums">{share === null ? (hidden ? "ปกปิดสัดส่วน" : "ไม่มีข้อมูล") : `${yes?.households ?? 0} จาก ${total} บ้านมีแอร์ (${q2Percent(share)})`}</span>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-sand" aria-hidden="true">
                {share !== null && <div className="h-full rounded-full bg-[#25877c]" style={{ width: `${share}%` }} />}
              </div>
            </li>
          );
        })}
      </ul>
      <Axis />
      <p className="mt-3 text-sm text-muted">ถ้าแต่ละช่วงรายได้มีสัดส่วนการมีแอร์ต่างกัน ควรดูรายได้ประกอบเวลาตีความผลค่าไฟระหว่างบ้านมีแอร์กับไม่มีแอร์</p>
    </figure>
  );
}
