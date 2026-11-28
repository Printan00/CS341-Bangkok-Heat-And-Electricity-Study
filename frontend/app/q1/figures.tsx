import { DashboardCardTitle } from "../dashboard-ui";
import type { Q1Row } from "../../lib/q1-data";
import { levels } from "./labels";

const ventilation = [
  ["good", "ดี"], ["moderate", "ปานกลาง"], ["poor", "ไม่ดี"], ["unknown", "ไม่ระบุ / ไม่แน่ใจ"],
] as const;
const bands = [
  ["0-1", "0–1"], ["2", "2"], ["3", "3"], ["4-5", "4–5"], ["unknown", "ไม่ระบุ"],
] as const;
export function WallHeatmap({ rows }: { rows: Q1Row[] }) {
  const cells = rows.filter(({ kind }) => kind === "heatmap");

  return (
    <section className="panel min-w-0 p-4 compact:p-5" aria-labelledby="q1-heatmap">
      <DashboardCardTitle question="Q1" id="q1-heatmap" title="ผนังและการระบายอากาศ" />
      <p className="mt-1 text-sm text-muted">คะแนนผลกระทบเฉลี่ย 0–13 คะแนน สีเข้มขึ้นเมื่อคะแนนสูงขึ้น</p>
      <div className="mt-3 overflow-hidden rounded-lg border border-line">
        <table className="w-full table-fixed text-center text-xs">
          <caption className="sr-only">คะแนนผลกระทบเฉลี่ยตามวัสดุผนังและการระบายอากาศ</caption>
          <thead className="bg-sand font-semibold">
            <tr><th scope="col" className="px-1 py-2">การระบายอากาศ</th><th scope="col" className="p-2">ผนังไม้</th><th scope="col" className="p-2">ผนังวัสดุอื่น</th></tr>
          </thead>
          <tbody>
            {ventilation.filter(([key]) => key !== "unknown" || cells.some(({ dimension }) => dimension === key)).map(([key, label]) => (
              <tr key={key} className="border-t border-line">
                <th scope="row" className="p-2 font-semibold">{label}</th>
                {["wood", "other"].map((wall) => {
                  const row = cells.find(({ dimension, label }) => dimension === key && label === wall);
                  const score = row?.value;
                  return (
                    <td key={wall} className="border-l border-line px-1 py-2" style={{ backgroundColor: score == null ? undefined : `color-mix(in srgb, #c75324 ${score / 13 * 72}%, #fff5ea)` }}>
                      <strong className="block text-base leading-tight tabular-nums">{score?.toFixed(2) ?? "—"}</strong>
                      {row?.households != null && <span>{row.households} บ้าน</span>}
                      {row?.suppressed && <span className="block text-muted">ปกปิด</span>}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-3 flex items-center gap-2 text-[10px] text-muted" aria-hidden="true">
        <span>0</span><div className="h-2 w-28 rounded-full bg-linear-to-r from-[#fff5ea] to-[#d38060]" /><span>13 คะแนน</span>
      </div>
    </section>
  );
}

export function HousingScore({ rows }: { rows: Q1Row[] }) {
  const values = rows.filter(({ kind }) => kind === "housing");
  const bandThree = values.find(({ label }) => label === "3")?.value;
  const bandFourFive = values.find(({ label }) => label === "4-5")?.value;
  return (
    <section className="panel min-w-0 p-4 compact:p-5" aria-labelledby="q1-housing">
      <DashboardCardTitle question="Q1" id="q1-housing" title="คะแนนสภาพบ้าน" />
      <p className="mt-1 text-sm text-muted">เปรียบเทียบผลกระทบเฉลี่ยตามคะแนนสภาพบ้านเสี่ยงร้อน 0–5</p>
      <ul className="mt-3 space-y-1.5">
        {bands.filter(([key]) => key !== "unknown" || values.some(({ label }) => label === key)).map(([key, label]) => {
          const row = values.find(({ label }) => label === key);
          return (
            <li key={key} className="grid grid-cols-[5.2rem_minmax(0,1fr)_2.9rem] items-center gap-2 text-xs">
              <span><strong className="font-semibold">{label}</strong>{row?.households != null && <span className="ml-1 text-muted">· {row.households} บ้าน</span>}</span>
              <span className="relative block h-px bg-line" aria-hidden="true">
                {row?.value != null && <span className="absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-heat" style={{ left: `${row.value / 13 * 100}%` }} />}
              </span>
              <strong className="text-right font-semibold tabular-nums">{row?.value?.toFixed(2) ?? "—"}</strong>
            </li>
          );
        })}
      </ul>
      <div className="mt-2 grid grid-cols-[5.2rem_minmax(0,1fr)_2.9rem] gap-2 text-[10px] text-muted" aria-hidden="true">
        <div className="col-start-2 flex justify-between border-t border-line pt-1"><span>0</span><span>6.5</span><span>13</span></div>
      </div>
      <p className="mt-2 text-xs text-muted">แกนนอนคือคะแนนผลกระทบความร้อน
        {bandThree != null && bandFourFive != null && bandThree > bandFourFive && " · กลุ่มคะแนนสภาพบ้าน 3 มีผลกระทบเฉลี่ยสูงกว่ากลุ่ม 4–5 ในตัวอย่างนี้"}
      </p>
    </section>
  );
}

export function ImpactDistribution({ rows }: { rows: Q1Row[] }) {
  const values = rows.filter(({ kind }) => kind === "distribution");
  const hidden = values.some(({ suppressed }) => suppressed);
  const total = hidden ? null : values.reduce((n, row) => n + (row.households ?? 0), 0);

  return (
    <section className="panel min-w-0 p-4 compact:p-5" aria-labelledby="q1-distribution">
      <DashboardCardTitle question="Q1" id="q1-distribution" title="ระดับผลกระทบในกลุ่มตัวอย่าง" />
      <p className="mt-1 text-sm text-muted">{total ? `บ้านที่มีข้อมูลครบ ${total} ครัวเรือน` : "จำนวนครัวเรือนตามระดับผลกระทบ"}</p>
      {total ? (
        <>
          <div className="mt-4 flex h-8 overflow-hidden rounded-md" aria-hidden="true">
            {levels.map(({ key, color, text }) => {
              const n = values.find(({ label }) => label === key)?.households ?? 0;
              const share = n / total * 100;
              return (
                <div key={key} className={`grid min-w-0 place-items-center text-[11px] font-semibold ${color} ${text}`} style={{ width: `${share}%` }}>
                  {share >= 15 && `${share.toFixed(1)}%`}
                </div>
              );
            })}
          </div>
          <ul className="mt-3 grid grid-cols-3 gap-1.5">
            {levels.map(({ key, label, range, color }) => {
              const n = values.find((row) => row.label === key)?.households ?? 0;
              return <li key={key} className="text-xs"><span className={`mr-1 inline-block size-2.5 rounded-sm ${color}`} aria-hidden="true" /><strong>{label}</strong><span className="block text-muted">{n} บ้าน · {(100 * n / total).toFixed(1)}%<br />{range} คะแนน</span></li>;
            })}
          </ul>
        </>
      ) : <p className="mt-3 text-xs text-muted">ข้อมูลไม่เพียงพอหรือถูกปกปิดตามกฎกลุ่มตัวอย่างขนาดเล็ก</p>}
    </section>
  );
}
