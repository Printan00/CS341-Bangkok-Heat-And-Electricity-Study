import type { CSSProperties } from "react";
import { ArrowUpRight } from "lucide-react";
import { DashboardCardTitle } from "./dashboard-ui";
import { percent, type Comparison } from "../lib/dashboard-data";

const ticks = [0, 25, 50, 75, 100];

function BarChart({ rows, label }: { rows: Comparison[]; label: string }) {
  return (
    <figure className="my-2 @container">
      <figcaption className="mb-1.5 text-[13px] text-muted">{label}</figcaption>
      <ul className="grid auto-rows-[minmax(27px,auto)]">
        {rows.map(({ label, detail, count }) => {
          const value = percent(...count);

          return (
            <li className="chart-row" key={label}>
              <span className="justify-self-end text-right text-[13px] leading-[1.16]">{label}{detail && <small className="block text-[10px] text-muted">{detail}</small>}</span>
              <span className="bar-track" style={{ "--bar-width": `${value ?? 0}%` } as CSSProperties}>
                <span className="bar bg-[#25877c]" aria-hidden="true" />
                <span className="bar-value">{value === null ? "—" : `${value}%`}</span>
              </span>
            </li>
          );
        })}
      </ul>
      <div className="chart-axis" aria-hidden="true">
        <div className="col-start-2 flex justify-between border-t border-[#d5cec4] pt-0.5 text-[10px] text-muted tabular-nums">{ticks.map((tick) => <span key={tick}>{tick}%</span>)}</div>
      </div>
    </figure>
  );
}

export function ElectricityChart({ rows }: { rows: Comparison[] }) {
  const low = percent(...rows[0].count);
  const high = percent(...rows[2].count);

  return (
    <article className="panel flex min-w-0 flex-col p-4" id="electricity" aria-labelledby="electricity-title">
      <DashboardCardTitle question="Q2" id="electricity-title" title="สัดส่วนภาระค่าไฟสูงตามช่วงรายได้" />
      <BarChart rows={rows} label="สัดส่วนครัวเรือนที่มีภาระค่าไฟสูงในแต่ละช่วงรายได้" />
      <p className="takeaway bg-energy-soft text-[#145950]">
        <ArrowUpRight size={16} aria-hidden="true" />
        <span>{low === null || high === null ? "กลุ่มตัวอย่างไม่ครบสำหรับการเปรียบเทียบ" : <>สัดส่วนครัวเรือนที่มีภาระค่าไฟสูงอยู่ที่ <strong>{low}%</strong> ในกลุ่มรายได้ไม่เกิน 10,000 บาท เทียบกับ <strong>{high}%</strong> ในกลุ่มรายได้มากกว่า 20,000 บาท</>}</span>
      </p>
    </article>
  );
}
