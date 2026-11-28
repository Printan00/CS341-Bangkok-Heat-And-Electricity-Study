"use client";

import { ArrowDown, ArrowDownUp, ArrowUp, Search } from "lucide-react";
import { useState } from "react";
import type { Q1Row } from "../../lib/q1-data";
import { analysisLabels, groupLabel, housingFeatures } from "./labels";

const columns = [
  ["analysis", "ชุดวิเคราะห์"], ["group", "กลุ่ม"], ["households", "จำนวนบ้าน"],
  ["low", "ต่ำ"], ["medium", "กลาง"], ["high", "สูง"], ["percent", "% สูง"], ["average", "เฉลี่ย (0–13)"], ["status", "หมายเหตุ"],
] as const;
type SortKey = (typeof columns)[number][0];

const collator = new Intl.Collator("th", { numeric: true });
const analysisOptions = Object.entries(analysisLabels);

function displayAnalysis(row: Q1Row) {
  if (row.kind === "comparison" || row.kind === "feature_detail") {
    const feature = housingFeatures[row.dimension]?.label ?? row.dimension;
    return `${analysisLabels[row.kind]} · ${feature}`;
  }
  if (row.kind === "profile") return row.dimension === "coping" ? "ระดับผลกระทบตามการรับมือ" : "ระดับผลกระทบตามคะแนนสภาพบ้าน";
  return analysisLabels[row.kind];
}

export function Q1ResultsTable({ rows }: { rows: Q1Row[] }) {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [sort, setSort] = useState<{ key: SortKey; asc: boolean }>();
  const query = search.trim().toLocaleLowerCase("th");
  const filtered = rows.filter(({ kind }) => !category || kind === category).map((row) => ({
    key: `${row.kind}:${row.dimension}:${row.label}`,
    analysis: displayAnalysis(row),
    group: groupLabel(row),
    households: row.households,
    low: row.low,
    medium: row.medium,
    high: row.high,
    percent: row.kind === "comparison" || row.kind === "profile" ? row.value : null,
    average: row.kind === "comparison" || row.kind === "profile" ? null : row.value,
    status: row.suppressed ? "ปกปิด" : null,
  })).filter(({ analysis, group }) => !query || `${analysis} ${group}`.toLocaleLowerCase("th").includes(query));

  const visible = sort ? filtered.toSorted((a, b) => {
    const first = a[sort.key];
    const second = b[sort.key];
    if (first === null || second === null) return Number(first === null) - Number(second === null);
    const comparison = typeof first === "number" && typeof second === "number"
      ? first - second : collator.compare(String(first), String(second));
    return sort.asc ? comparison : -comparison;
  }) : filtered;
  // Each analysis fills only some columns; hide those that are empty for every visible row.
  const shownColumns = columns.filter(([key]) => key === "analysis" || key === "group" || key === "households"
    || visible.some((row) => row[key] !== null));

  return (
    <section className="mt-6" id="q1-table" aria-labelledby="q1-table-title">
      <h2 id="q1-table-title" className="section-title">ตารางข้อมูล Q1 ทั้งหมด</h2>
      <p className="mt-1 mb-3 text-sm text-muted">ผลสรุปทุกชุดที่ใช้วาดกราฟ ค้นหาชื่อกลุ่มหรือเลือกชุดวิเคราะห์ แล้วกดหัวคอลัมน์เพื่อเรียง</p>
      <div className="panel p-3 compact:p-4">
        <div className="flex flex-wrap items-end gap-2">
          <label className="grid w-full gap-1 text-xs font-medium compact:max-w-64">
            ค้นหาชุดวิเคราะห์หรือกลุ่ม
            <span className="relative">
              <Search size={15} className="pointer-events-none absolute top-1/2 left-2 -translate-y-1/2 text-muted" aria-hidden="true" />
              <input type="search" value={search} onChange={(event) => setSearch(event.target.value)}
                className="h-9 w-full rounded-lg border border-line bg-white pr-2 pl-7 text-sm" />
            </span>
          </label>
          <label className="grid w-full gap-1 text-xs font-medium compact:w-auto">
            ชุดวิเคราะห์
            <select value={category} onChange={(event) => setCategory(event.target.value)} className="h-9 rounded-lg border border-line bg-white px-2 text-sm">
              <option value="">ทุกชุดวิเคราะห์</option>
              {analysisOptions.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
            </select>
          </label>
          <p role="status" className="text-xs text-muted compact:ml-auto compact:self-end compact:pb-2">แสดง {visible.length} จาก {rows.length} แถว</p>
        </div>

        <div role="region" aria-labelledby="q1-table-title" tabIndex={0} className="mt-3 max-h-[34rem] overflow-auto rounded-lg border border-line">
          <table className="w-full min-w-[805px] border-separate border-spacing-0 text-left text-xs">
            <caption className="sr-only">ผลสรุประดับกลุ่มของ Q1</caption>
            <thead className="sticky top-0 z-10 bg-sand">
              <tr>
                {shownColumns.map(([key, label]) => {
                  const active = sort?.key === key;
                  const Icon = active ? (sort.asc ? ArrowUp : ArrowDown) : ArrowDownUp;
                  return (
                    <th key={key} scope="col" aria-sort={active ? (sort.asc ? "ascending" : "descending") : undefined}>
                      <button type="button" onClick={() => setSort((previous) => ({ key, asc: previous?.key !== key || !previous.asc }))}
                        className="flex min-h-9 w-full items-center gap-1 whitespace-nowrap px-2 text-left hover:text-heat focus-visible:outline-offset-[-3px]">{label}<Icon size={12} className="shrink-0" aria-hidden="true" /></button>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {visible.map((row) => (
                <tr key={row.key} className="odd:bg-white even:bg-canvas">
                  {shownColumns.map(([key]) => {
                    const value = row[key];
                    const display = typeof value === "number" && (key === "percent" || key === "average")
                      ? `${value.toFixed(key === "percent" ? 1 : 2)}${key === "percent" ? "%" : ""}`
                      : value ?? <span className="text-[#cfc8bc]" aria-label="ไม่มีค่า">–</span>;
                    return key === "group"
                      ? <th key={key} scope="row" className="border-t border-line px-2 py-2 font-medium">{display}</th>
                      : <td key={key} className={`border-t border-line px-2 py-2 tabular-nums ${key === "status" && row.status === "ปกปิด" ? "text-heat" : ""}`}>{display}</td>;
                  })}
                </tr>
              ))}
              {!visible.length && <tr><td colSpan={shownColumns.length} className="px-2 py-3 text-muted">ไม่พบกลุ่มที่ตรงกับตัวกรอง</td></tr>}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-muted">ขีดสีจางหมายถึงชุดวิเคราะห์นั้นไม่ได้ใช้ค่านี้ เช่น ชุดเปรียบเทียบใช้ % สูง ส่วนชุดคะแนนเฉลี่ยใช้ค่าเฉลี่ย 0–13 เลือกชุดวิเคราะห์เพื่อซ่อนคอลัมน์ที่ไม่ใช้ แถวที่มีคำว่าปกปิดคือกลุ่มขนาดเล็กที่ซ่อนตัวเลขไว้ จำนวนบ้านในแต่ละชุดนับครัวเรือนเดิมซ้ำได้ จึงไม่ควรบวกข้ามชุด</p>
      </div>
    </section>
  );
}
