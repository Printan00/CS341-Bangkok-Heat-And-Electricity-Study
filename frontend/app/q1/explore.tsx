"use client";

import { useState } from "react";
import type { Q1Row } from "../../lib/q1-data";
import { groupLabel, housingFeatures } from "./labels";

export function AverageBars({ rows }: { rows: Q1Row[] }) {
  if (!rows.length) return <p className="mt-3 text-sm text-muted">ยังไม่มีข้อมูลสำหรับการเปรียบเทียบนี้</p>;

  return (
    <>
      <ul className="mt-3 space-y-2">
        {rows.toSorted((a, b) => (b.value ?? -1) - (a.value ?? -1)).map((row) => (
          <li key={row.label} className="grid grid-cols-[minmax(6.8rem,34%)_minmax(0,1fr)_2.8rem] items-center gap-2">
            <span className="text-xs leading-tight"><strong className="block font-semibold">{groupLabel(row)}</strong>
              {row.households != null && <span className="block text-muted">{row.households} บ้าน</span>}
            </span>
            <span aria-hidden="true" className="block h-4 rounded-sm bg-sand">
              {row.value != null && <span className="block h-full rounded-sm bg-heat" style={{ width: `${row.value / 13 * 100}%` }} />}
            </span>
            <span className="text-right text-xs font-semibold tabular-nums">{row.suppressed
              ? <span aria-label="ปกปิดข้อมูล">—</span> : row.value?.toFixed(2) ?? "—"}</span>
          </li>
        ))}
      </ul>
      <div className="mt-1 grid grid-cols-[minmax(6.8rem,34%)_minmax(0,1fr)_2.8rem] gap-2 text-[10px] text-muted" aria-hidden="true">
        <div className="col-start-2 flex justify-between border-t border-line pt-1"><span>0</span><span>6.5</span><span>13</span></div>
      </div>
    </>
  );
}

const notes: Record<string, string> = {
  housing_type: "กลุ่มที่อยู่อาศัยอื่นรวมหลายรูปแบบตามการจัดกลุ่มของงานวิจัย",
  wall: "กราฟนี้แยกคอนกรีตออกจากผนังผสมและวัสดุอื่น เพื่อเห็นความแตกต่างในกลุ่มเปรียบเทียบ",
  roof: "กลุ่มวัสดุอื่นรวมกระเบื้อง คอนกรีต วัสดุอื่น และบ้านที่ไม่ระบุ",
  ceiling: "กลุ่มมีฝ้ารวมผู้ตอบที่ไม่แน่ใจตามการจัดกลุ่มของงานวิจัย",
  insulation: "ดูจำนวนบ้านประกอบ เพราะบ้านสองกลุ่มมีขนาดต่างกันมาก",
  ventilation: "แยกดี ปานกลาง และไม่ดีตามการระบายอากาศที่ผู้ตอบรายงาน",
  shade: "ร่มเงาเป็นระดับที่ผู้ตอบรายงานเอง ค่าเฉลี่ยใช้เปรียบเทียบเชิงพรรณนา",
};

export function HousingExplorer({ rows }: { rows: Q1Row[] }) {
  const [selected, setSelected] = useState("housing_type");

  return (
    <section id="q1-detail" aria-labelledby="q1-detail-title" className="mt-6">
      <h2 id="q1-detail-title" className="section-title">เจาะรายละเอียดลักษณะบ้าน</h2>
      <p className="mt-1 mb-3 text-sm text-muted">เลือกปัจจัยเพื่อเปรียบเทียบคะแนนผลกระทบเฉลี่ย (0–13) และจำนวนบ้านในแต่ละกลุ่ม</p>
      <div className="panel p-4 compact:p-5">
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="เลือกรายละเอียดลักษณะบ้าน">
          {Object.entries(housingFeatures).map(([key, feature]) => (
            <button key={key} type="button" aria-pressed={selected === key} onClick={() => setSelected(key)}
              className="rounded-lg border border-line px-2.5 py-1.5 text-xs font-medium hover:border-heat aria-pressed:border-heat aria-pressed:bg-heat aria-pressed:text-white">{feature.label}</button>
          ))}
        </div>
        <div className="mt-3" aria-live="polite">
          <h3 className="font-bold">คะแนนเฉลี่ยตาม{housingFeatures[selected].label}</h3>
          <AverageBars rows={rows.filter(({ kind, dimension }) => kind === "feature_detail" && dimension === selected)} />
          <p className="mt-2 text-xs text-muted">{notes[selected]}</p>
        </div>
      </div>
    </section>
  );
}
