"use client";

import { ArrowDown, ArrowDownUp, ArrowUp } from "lucide-react";
import { useId, useState } from "react";
import type { RiskMetric, RiskRow } from "../lib/q3-data";
import { groupInfo } from "../lib/q3-groups";

type SortKey = "priority" | "group" | "households" | RiskMetric;
type Direction = "asc" | "desc";

const columns: { key: SortKey; label: string }[] = [
  { key: "priority", label: "ลำดับ" },
  { key: "group", label: "กลุ่มความเสี่ยง" },
  { key: "households", label: "จำนวนบ้าน" },
  { key: "risk_score", label: "เสี่ยงรวม" },
  { key: "exposure", label: "เผชิญความร้อน" },
  { key: "vulnerability", label: "เปราะบาง" },
  { key: "heat", label: "ผลกระทบความร้อน" },
  { key: "housing", label: "สภาพบ้าน" },
  { key: "finance", label: "การเงิน" },
  { key: "burden", label: "ภาระค่าไฟ" },
  { key: "coping", label: "ข้อจำกัดการรับมือ" },
];

const thaiOrder = new Intl.Collator("th");
const scoreFormat = new Intl.NumberFormat("th-TH", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

function cellValue(row: RiskRow, key: SortKey) {
  if (key === "group") return groupInfo[row.group].label;
  if (key === "priority") return groupInfo[row.group].order;
  return row[key];
}

export function Q3Table({ rows, labelledBy }: { rows: RiskRow[]; labelledBy: string }) {
  const sortHelpId = useId();
  const [sort, setSort] = useState<{ key: SortKey; direction: Direction }>({ key: "priority", direction: "asc" });
  const ordered = rows.toSorted((a, b) => {
    const left = cellValue(a, sort.key);
    const right = cellValue(b, sort.key);
    if (left === null || right === null) return Number(left === null) - Number(right === null);
    const comparison = typeof left === "number" && typeof right === "number"
      ? left - right : thaiOrder.compare(String(left), String(right));
    return (sort.direction === "asc" ? comparison : -comparison) || groupInfo[a.group].order - groupInfo[b.group].order;
  });

  function sortBy(key: SortKey) {
    setSort((current) => ({
      key,
      direction: current.key === key ? (current.direction === "asc" ? "desc" : "asc")
        : key === "priority" || key === "group" ? "asc" : "desc",
    }));
  }

  return (
    <>
      <p className="mb-2 text-xs text-muted" id={sortHelpId}>กดหัวคอลัมน์เพื่อเรียงลำดับ บนจอเล็กเลื่อนตารางด้านข้างเพื่อดูคะแนนทั้งหมด</p>
      <div className="panel overflow-x-auto" role="region" aria-labelledby={labelledBy} tabIndex={0}>
        <table className="w-full min-w-[990px] border-collapse text-left text-xs" aria-describedby={sortHelpId}>
          <caption className="sr-only">จำนวนครัวเรือนและคะแนนเฉลี่ยตามกลุ่มความเสี่ยง</caption>
          <thead className="bg-sand font-semibold text-muted">
            <tr>
              {columns.map(({ key, label }) => {
                const active = sort.key === key;
                const Icon = active ? (sort.direction === "asc" ? ArrowUp : ArrowDown) : ArrowDownUp;
                return (
                  <th key={key} scope="col" aria-sort={active ? (sort.direction === "asc" ? "ascending" : "descending") : undefined}>
                    <button type="button" onClick={() => sortBy(key)} className="flex min-h-10 w-full items-center gap-1 whitespace-nowrap px-2 text-left hover:text-ink focus-visible:outline-offset-[-3px]">
                      {label}<Icon size={13} aria-hidden="true" className={active ? "text-heat" : ""} />
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {ordered.map((row) => (
              <tr key={row.group} className={`border-t border-line ${row.group === "help_first" ? "bg-heat-soft/45" : ""}`}>
                {columns.map(({ key }) => {
                  const value = cellValue(row, key);
                  if (key === "group") return <th key={key} scope="row" className="px-2 py-2 font-semibold">{value}</th>;
                  return (
                    <td key={key} className="px-2 py-2 text-right tabular-nums">
                      {value === null ? <span className="text-muted" title={row.suppressed ? "ปกปิดข้อมูลกลุ่มตัวอย่างขนาดเล็ก" : "ข้อมูลไม่เพียงพอ"}>—</span>
                        : key === "priority" || key === "households" ? value : scoreFormat.format(Number(value))}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-muted">คะแนนเป็นค่าเฉลี่ย 0–100 คะแนนสูงหมายถึงเสี่ยงมากขึ้น กลุ่มช่วยก่อนมีคะแนนทั้งสองแกนอย่างน้อย 0.5 ก่อนแปลงสเกล</p>
      {rows.some(({ suppressed }) => suppressed) && <p className="mt-1 text-xs text-muted">ปกปิดจำนวนและคะแนนเมื่อกลุ่มตัวอย่างมีขนาดเล็ก</p>}
    </>
  );
}
