import type { Q1Row } from "../../lib/q1-data";
import { AverageBars } from "./explore";
import { groupLabel, levels } from "./labels";

function ProfileCard({ rows, title, note, id }: { rows: Q1Row[]; title: string; note: string; id: string }) {
  return (
    <section className="panel min-w-0 p-4 compact:p-5" aria-labelledby={id}>
      <h3 className="text-base font-bold" id={id}>{title}</h3>
      <ul className="mt-2 flex flex-wrap gap-3 text-xs text-muted" aria-label="ระดับผลกระทบ">
        {levels.map(({ key, label, color }) => <li key={key}><span className={`mr-1 inline-block size-2.5 rounded-sm ${color}`} aria-hidden="true" />{label}</li>)}
      </ul>
      <ul className="mt-3 space-y-3">
        {rows.map((row) => {
          const total = row.households;
          return (
          <li key={row.label}>
            <p className="text-xs font-semibold">{groupLabel(row)} {total != null && <span className="font-normal text-muted">· {total} บ้าน</span>}</p>
            {total != null && total > 0 ? (
              <>
                <div className="mt-1 flex h-6 overflow-hidden rounded-md" aria-hidden="true">
                  {levels.map(({ key, color, text }) => {
                    const share = (row[key] ?? 0) / total * 100;
                    return <span key={key} className={`grid min-w-0 place-items-center overflow-hidden text-[10px] font-semibold ${color} ${text}`} style={{ width: `${share}%` }}>{share >= 15 ? `${share.toFixed(1)}%` : ""}</span>;
                  })}
                </div>
                <p className="mt-1 text-[11px] text-muted">{levels.map(({ key, label }) => `${label} ${row[key] ?? "—"} บ้าน`).join(" · ")}</p>
              </>
            ) : <p className="mt-1 text-xs text-muted">{row.suppressed ? "ปกปิดข้อมูลกลุ่มขนาดเล็ก" : "ข้อมูลไม่เพียงพอ"}</p>}
          </li>
          );
        })}
      </ul>
      <p className="mt-3 text-xs text-muted">{note}</p>
    </section>
  );
}

export function HouseholdContext({ rows }: { rows: Q1Row[] }) {
  return (
    <section id="q1-context" aria-labelledby="q1-context-title" className="mt-6">
      <h2 id="q1-context-title" className="section-title">บริบทของครัวเรือน</h2>
      <p className="mt-1 mb-3 text-sm text-muted">ดูระดับผลกระทบควบคู่กับชุมชน ความสามารถรับมือ และคะแนนสภาพบ้าน</p>
      <div className="grid gap-3 @min-[44rem]:grid-cols-2">
        <section className="panel min-w-0 p-4 compact:p-5" aria-labelledby="q1-community">
          <h3 id="q1-community" className="text-base font-bold">คะแนนผลกระทบเฉลี่ยตามชุมชน</h3>
          <AverageBars rows={rows.filter(({ kind }) => kind === "community")} />
          <p className="mt-2 text-xs text-muted">คะแนนเต็ม 13 ใช้ดูบริบทของกลุ่มตัวอย่าง โดยกลุ่มไม่ทราบชุมชนรวมผู้ที่จัดเข้าชุมชนไม่ได้</p>
        </section>
        <ProfileCard id="q1-coping" title="ระดับผลกระทบตามความสามารถรับมือ"
          rows={rows.filter(({ kind, dimension }) => kind === "profile" && dimension === "coping")}
          note="รับมือได้จำกัดหมายถึงมีข้อจำกัดอย่างน้อย 3 จาก 6 ด้าน ตามเกณฑ์ของโครงการ" />
        <div className="@min-[44rem]:col-span-2">
          <ProfileCard id="q1-risk-band" title="ระดับผลกระทบตามกลุ่มคะแนนสภาพบ้าน"
            rows={rows.filter(({ kind, dimension }) => kind === "profile" && dimension === "housing_risk")}
            note="กลุ่ม 0–2 และ 3–5 มาจากคะแนนสภาพบ้าน ส่วนความยาวแต่ละช่วงคือสัดส่วนผลกระทบในกลุ่มนั้น" />
        </div>
      </div>
    </section>
  );
}
