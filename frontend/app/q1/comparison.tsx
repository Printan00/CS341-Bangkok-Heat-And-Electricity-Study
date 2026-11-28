"use client";

import { useState } from "react";
import { DashboardCardTitle } from "../dashboard-ui";
import type { Q1Results } from "../../lib/q1-data";

const features = [
  { key: "wall", label: "วัสดุผนัง", first: "ผนังไม้", second: "ผนังวัสดุอื่น", group: "wood" },
  { key: "ventilation", label: "ระบายอากาศ", first: "ระบายอากาศไม่ดี", second: "ปานกลาง / ดี / อื่น ๆ", group: "poor" },
  { key: "roof", label: "หลังคา", first: "สังกะสี / เมทัลชีท", second: "หลังคาวัสดุอื่น", group: "metal" },
  { key: "ceiling", label: "ฝ้าเพดาน", first: "ไม่มีฝ้า", second: "มีฝ้า / ไม่แน่ใจ", group: "absent" },
] as const;

export function FeatureComparison({ rows, pValues }: Q1Results) {
  const [selected, setSelected] = useState<(typeof features)[number]>(features[0]);
  const groups = rows.filter((row) => row.kind === "comparison" && row.dimension === selected.key);
  const p = pValues[selected.key];

  return (
    <section className="panel min-w-0 p-4 compact:p-5" aria-labelledby="q1-comparison">
      <DashboardCardTitle question="Q1" id="q1-comparison" title="เปรียบเทียบตามลักษณะบ้าน" />
      <p className="mt-1 text-sm text-muted">สัดส่วนครัวเรือนที่ได้รับผลกระทบสูงในแต่ละกลุ่ม</p>
      <div className="mt-3 flex flex-wrap gap-1.5" role="group" aria-label="เลือกลักษณะบ้าน">
        {features.map((feature) => (
          <button
            key={feature.key}
            type="button"
            aria-pressed={selected.key === feature.key}
            onClick={() => setSelected(feature)}
            className="rounded-lg border border-line px-2.5 py-1.5 text-[13px] font-medium hover:border-heat aria-pressed:border-heat aria-pressed:bg-heat aria-pressed:text-white"
          >
            {feature.label}
          </button>
        ))}
      </div>
      <div className="mt-4" aria-live="polite">
        <div className="space-y-2">
          {[selected.group, "other"].map((key, index) => {
            const row = groups.find(({ label }) => key === label);
            return (
              <div key={key} className="grid grid-cols-[5.5rem_minmax(0,1fr)_3.2rem] compact:grid-cols-[6.8rem_minmax(0,1fr)_3.8rem] items-center gap-2">
                <div className="text-xs leading-tight">
                  <strong className="block font-semibold">{index === 0 ? selected.first : selected.second}</strong>
                  {row?.households != null && row.high != null && <span className="mt-1 block text-muted">{row.high} / {row.households} บ้าน</span>}
                </div>
                <div className="h-4 rounded-sm bg-sand" aria-hidden="true">
                  {row?.value != null && <div className={`h-full rounded-sm ${index === 0 ? "bg-heat" : "bg-[#caaa73]"}`} style={{ width: `${row.value}%` }} />}
                </div>
                <strong className="text-right font-semibold tabular-nums">{row?.value == null ? "—" : `${row.value.toFixed(1)}%`}</strong>
              </div>
            );
          })}
        </div>
        <div className="mt-1 grid grid-cols-[5.5rem_minmax(0,1fr)_3.2rem] compact:grid-cols-[6.8rem_minmax(0,1fr)_3.8rem] gap-2 text-[10px] text-muted" aria-hidden="true">
          <div className="col-start-2 flex justify-between border-t border-line pt-1"><span>0%</span><span>50%</span><span>100%</span></div>
        </div>
        {p !== undefined ? (
          <p className="mt-3 border-t border-line pt-2 text-xs text-muted">
            Fisher แบบสองด้าน <span className="font-semibold text-ink">p {p < 0.001 ? "< 0.001" : `= ${p.toFixed(3)}`}</span>
            <span> · {p < 0.05 ? "พบความสัมพันธ์ที่ระดับ 0.05" : "หลักฐานยังไม่พอที่ระดับ 0.05"} · ยังไม่ได้ปรับสำหรับการทดสอบหลายคู่</span>
          </p>
        ) : <p className="mt-3 text-xs text-muted">ข้อมูลไม่เพียงพอหรือถูกปกปิดตามกฎกลุ่มตัวอย่างขนาดเล็ก</p>}
      </div>
    </section>
  );
}
