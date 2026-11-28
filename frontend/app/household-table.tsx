"use client";

import { ArrowDown, ArrowDownUp, ArrowUp } from "lucide-react";
import { useState } from "react";

export type HouseholdCell = number | string | boolean | null;
export type HouseholdData = {
  columns: string[];
  rows: Record<string, HouseholdCell>[];
};

export type HouseholdColumnOptions = Record<string, {
  label: string;
  values?: Record<string, string>;
  order?: string[];
  percentage?: boolean;
  /** fixed decimals for numbers; default: integers as-is, others 2 decimals */
  decimals?: number;
}>;

const orderText = new Intl.Collator("en", { numeric: true });

export function HouseholdTable({ columns, rows, options, showRowNumbers = false }: HouseholdData & {
  options?: HouseholdColumnOptions;
  showRowNumbers?: boolean;
}) {
  const [sort, setSort] = useState({ key: "risk_rank", ascending: true });
  const ordered = rows.toSorted((a, b) => {
    const left = a[sort.key];
    const right = b[sort.key];
    if (left == null || right == null) return Number(left == null) - Number(right == null);
    const order = options?.[sort.key]?.order;
    const delta = order ? order.indexOf(String(left)) - order.indexOf(String(right))
      : typeof left === "number" && typeof right === "number" ? left - right
        : orderText.compare(String(left), String(right));
    return sort.ascending ? delta : -delta;
  });

  function displayCell(key: string, value: HouseholdCell) {
    if (value == null) return "—";
    const column = options?.[key];
    if (column?.percentage && typeof value === "number") return `${(100 * value).toFixed(1)}%`;
    if (typeof value === "number") {
      if (column?.decimals !== undefined) return value.toFixed(column.decimals);
      return Number.isInteger(value) ? String(value) : value.toFixed(2);
    }
    if (typeof value === "boolean") return column?.values?.[String(value)] ?? (value ? "ใช่" : "ไม่ใช่");
    return column?.values?.[value] ?? value;
  }

  return (
    <>
      <p className="mb-2 text-sm font-medium">{rows.length} แถว · {columns.length} คอลัมน์</p>
      <div className="panel max-h-[75vh] overflow-auto" role="region" aria-label="ตารางรายครัวเรือนแบบเลื่อน" tabIndex={0}>
        <table className="w-full border-separate border-spacing-0 text-left text-xs">
          <caption className="sr-only">ข้อมูลรายครัวเรือนจากไฟล์ Happy Home Risk ใน S3</caption>
          <thead className="sticky top-0 z-10 bg-sand">
            <tr>
              {showRowNumbers && <th scope="col" className="px-3" aria-label="แถวที่">#</th>}
              {columns.map((key) => {
                const active = sort.key === key;
                const Icon = active ? (sort.ascending ? ArrowUp : ArrowDown) : ArrowDownUp;
                return (
                  <th key={key} scope="col" aria-sort={active ? (sort.ascending ? "ascending" : "descending") : undefined}>
                    <button type="button" title={options?.[key] ? key : undefined} className="flex min-h-10 w-full items-center gap-1 whitespace-nowrap px-3 text-left hover:text-heat focus-visible:outline-offset-[-3px]" onClick={() => setSort((previous) => ({ key, ascending: previous.key !== key || !previous.ascending }))}>
                      {options?.[key]?.label ?? key}<Icon size={13} aria-hidden="true" className="shrink-0" />
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {ordered.map((row, index) => (
              <tr key={String(row.household_code)} className="odd:bg-white even:bg-sand/40">
                {showRowNumbers && <td className="border-t border-line px-3 py-2 text-muted tabular-nums">{index + 1}</td>}
                {columns.map((key) => (
                  <td key={key} className={`border-t border-line px-3 py-2 whitespace-nowrap tabular-nums ${key === "risk_quadrant" && row[key] === "help_first" ? "font-semibold text-heat" : ""}`}>{displayCell(key, row[key])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
