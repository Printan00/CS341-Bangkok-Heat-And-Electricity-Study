import type { CSSProperties } from "react";
import { ArrowUpRight, Thermometer, Zap } from "lucide-react";
import { percent, type Comparison } from "../lib/dashboard-data";

const ticks = [0, 25, 50, 75, 100];
const barTones = { heat: "bg-[#c45f38]", sand: "bg-[#d6b777]", energy: "bg-[#25877c]" };

function BarChart({ rows, label }: { rows: Comparison[]; label: string }) {
  return (
    <figure className="my-2 @container">
      <figcaption className="mb-1.5 text-[13px] text-muted">{label}</figcaption>
      <ul className="grid auto-rows-[minmax(27px,auto)]">
        {rows.map(({ label, detail, count, tone }) => {
          const value = percent(...count);

          return (
            <li className="chart-row" key={label}>
              <span className="justify-self-end text-right text-[13px] leading-[1.16]">{label}{detail && <small className="block text-[10px] text-muted">{detail}</small>}</span>
              <span className="bar-track" style={{ "--bar-width": `${value ?? 0}%` } as CSSProperties}>
                <span className={`bar ${barTones[tone]}`} aria-hidden="true" />
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

function groupDifference(first: Comparison, second: Comparison, description: string) {
  const firstValue = percent(...first.count);
  const secondValue = percent(...second.count);

  if (firstValue === null || secondValue === null) return "กลุ่มตัวอย่างไม่ครบสำหรับการเปรียบเทียบ";
  const difference = Math.abs(firstValue - secondValue);
  if (!difference) return `${description}มีสัดส่วนเท่ากันที่ ${firstValue}%`;

  const higher = firstValue > secondValue ? first : second;
  const lower = firstValue > secondValue ? second : first;
  return `${higher.label}มีสัดส่วน${description}สูงกว่า${lower.label} ${difference} จุดเปอร์เซ็นต์`;
}

export function HousingChart({ rows }: { rows: Comparison[] }) {
  return (
    <article className="panel flex min-w-0 flex-col p-3" id="heat" aria-labelledby="heat-title">
      <header className="flex items-start gap-2">
        <span className="question-icon bg-heat-soft text-heat"><Thermometer size={16} aria-hidden="true" /> Q1</span>
        <h3 id="heat-title" className="text-[clamp(16px,1.75cqi,19px)] leading-[1.35] font-bold">บ้านแบบไหนได้รับผลกระทบจากความร้อนมากกว่า?</h3>
      </header>
      <BarChart rows={rows} label="สัดส่วนครัวเรือนที่ได้รับผลกระทบสูงในแต่ละกลุ่ม" />
      <p className="takeaway bg-heat-soft text-[#76351d]"><ArrowUpRight size={16} aria-hidden="true" /><span>{groupDifference(rows[0], rows[1], "ครัวเรือนที่ได้รับผลกระทบสูง")}</span></p>
    </article>
  );
}

export function ElectricityChart({ rows }: { rows: Comparison[] }) {
  const low = percent(...rows[0].count);
  const high = percent(...rows[2].count);

  return (
    <article className="panel flex min-w-0 flex-col p-3" id="electricity" aria-labelledby="electricity-title">
      <header className="flex items-start gap-2">
        <span className="question-icon bg-energy-soft text-energy"><Zap size={16} aria-hidden="true" /> Q2</span>
        <h3 id="electricity-title" className="text-[clamp(16px,1.75cqi,19px)] leading-[1.35] font-bold">รายได้สัมพันธ์กับภาระค่าไฟอย่างไร?</h3>
      </header>
      <BarChart rows={rows} label="สัดส่วนครัวเรือนที่มีภาระค่าไฟสูงในแต่ละช่วงรายได้" />
      <p className="takeaway bg-energy-soft text-[#145950]">
        <ArrowUpRight size={16} aria-hidden="true" />
        <span>{low === null || high === null ? "กลุ่มตัวอย่างไม่ครบสำหรับการเปรียบเทียบ" : <>สัดส่วนครัวเรือนที่มีภาระค่าไฟสูงอยู่ที่ <strong>{low}%</strong> ในกลุ่มรายได้ไม่เกิน 10,000 บาท เทียบกับ <strong>{high}%</strong> ในกลุ่มรายได้มากกว่า 20,000 บาท</>}</span>
      </p>
    </article>
  );
}
