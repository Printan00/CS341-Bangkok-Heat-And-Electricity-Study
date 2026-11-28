import { ArrowDown } from "lucide-react";
import type { CSSProperties } from "react";

type Question = "Q1" | "Q2" | "Q3";

/** q = survey question, col = computed column, out = what the page shows */
export type FlowNode = { title: string; sub?: string; kind: "q" | "col" | "out" };

const resultTone: Record<Question, string> = {
  Q1: "border-heat/35 bg-heat-soft text-heat",
  Q2: "border-energy/35 bg-energy-soft text-energy",
  Q3: "border-olive/35 bg-olive-soft text-olive",
};

function Node({ node, question }: { node: FlowNode; question: Question }) {
  const style = node.kind === "q" ? "border-line bg-white"
    : node.kind === "col" ? "border-transparent bg-sand"
      : resultTone[question];
  return (
    <div className={`min-w-0 rounded-lg border px-2.5 py-1.5 leading-tight ${style}`}>
      <span className={`block text-[13px] font-semibold break-words ${node.kind === "col" ? "font-mono text-[12px] text-ink" : ""}`}>{node.title}</span>
      {node.sub && <span className={`mt-0.5 block text-[11px] ${node.kind === "out" ? "opacity-80" : "text-muted"}`}>{node.sub}</span>}
    </div>
  );
}

const lineColor = "bg-[#c9c1b4]";

/** Horizontal connector; `head` draws an arrowhead at the right end. */
function Line({ head }: { head?: boolean }) {
  return (
    <div className="relative h-full min-h-10" aria-hidden="true">
      <span className={`absolute top-1/2 left-0 h-px ${lineColor} ${head ? "right-1.5" : "right-0"}`} />
      {head && <span className="absolute top-1/2 right-0 -translate-y-1/2 border-y-[4px] border-l-[6px] border-y-transparent border-l-[#c9c1b4]" />}
    </div>
  );
}

/** Bracket piece joining each lane into the shared result. */
function Bracket({ index, count }: { index: number; count: number }) {
  const vertical = count === 1 ? null : index === 0 ? "top-1/2 bottom-0" : index === count - 1 ? "top-0 bottom-1/2" : "top-0 bottom-0";
  return (
    <div className="relative h-full min-h-10" aria-hidden="true">
      <span className={`absolute top-1/2 left-0 h-px ${lineColor} ${count === 1 ? "right-0" : "right-1/2"}`} />
      {vertical && <span className={`absolute left-1/2 w-px ${lineColor} ${vertical}`} />}
    </div>
  );
}

/**
 * Stage-by-stage flow: each lane runs left to right through the stage columns
 * (null = passes through), then all lanes join into one result box.
 */
export function FlowGrid({ question, stages, lanes, result, resultLabel, caption }: {
  question: Question;
  stages: string[];
  lanes: (FlowNode | null)[][];
  result: FlowNode;
  resultLabel: string;
  caption?: string;
}) {
  const columns = stages.flatMap((_, i) => (i === 0 ? ["minmax(6.5rem,1fr)"] : ["1.75rem", "minmax(6.5rem,1fr)"]));
  const template: CSSProperties = { gridTemplateColumns: [...columns, "1.75rem", "minmax(8rem,1fr)"].join(" ") };
  const cols = stages.length * 2 - 1;

  return (
    <figure className="min-w-0">
      {caption && <figcaption className="mb-2 text-xs font-semibold text-muted">{caption}</figcaption>}

      {/* wide screens: aligned stage columns */}
      <div className="hidden @min-[44rem]:grid" style={template}>
        {stages.map((stage, i) => (
          <p key={stage} className="pb-1.5 text-[11px] font-semibold tracking-wide text-muted uppercase" style={{ gridColumn: i * 2 + 1 }}>{stage}</p>
        ))}
        <p className="pb-1.5 text-[11px] font-semibold tracking-wide text-muted" style={{ gridColumn: cols + 2 }}>{resultLabel}</p>

        {lanes.map((lane, row) => lane.flatMap((node, i) => {
          const cells = [];
          if (i > 0) cells.push(<div key={`a${i}`} className="py-1" style={{ gridRow: row + 2, gridColumn: i * 2 }}><Line head={node !== null} /></div>);
          cells.push(
            <div key={`n${i}`} className="py-1" style={{ gridRow: row + 2, gridColumn: i * 2 + 1 }}>
              {node ? <Node node={node} question={question} /> : <Line />}
            </div>,
          );
          return cells;
        }).concat(
          <div key="b" style={{ gridRow: row + 2, gridColumn: cols + 1 }}><Bracket index={row} count={lanes.length} /></div>,
        ))}

        <div className="relative flex items-center py-1" style={{ gridColumn: cols + 2, gridRow: `2 / span ${lanes.length}` }}>
          <span className={`absolute top-1/2 right-full h-px w-[0.875rem] ${lineColor}`} aria-hidden="true" />
          <span className="absolute top-1/2 left-0 -translate-y-1/2 border-y-[4px] border-l-[6px] border-y-transparent border-l-[#c9c1b4]" aria-hidden="true" />
          <div className="w-full pl-2"><Node node={result} question={question} /></div>
        </div>
      </div>

      {/* narrow screens: one card per lane */}
      <ol className="space-y-2 @min-[44rem]:hidden">
        {lanes.map((lane, row) => (
          <li key={row} className="flex flex-wrap items-center gap-1.5 rounded-lg border border-line p-2">
            {lane.filter((node): node is FlowNode => node !== null).map((node, i) => (
              <span key={node.title} className="flex items-center gap-1.5">
                {i > 0 && <span className="text-muted" aria-hidden="true">→</span>}
                <Node node={node} question={question} />
              </span>
            ))}
          </li>
        ))}
        <li className="flex flex-col items-center gap-1" aria-label={resultLabel}>
          <ArrowDown size={16} className="text-muted" aria-hidden="true" />
          <div className="w-full"><Node node={result} question={question} /></div>
        </li>
      </ol>
    </figure>
  );
}

export function FlowLegend({ question }: { question: Question }) {
  return (
    <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 border-t border-line pt-2 text-[11px] text-muted" aria-label="คำอธิบายสัญลักษณ์">
      <li><span className="mr-1 inline-block size-2.5 rounded-sm border border-line bg-white align-middle" />ข้อในแบบสอบถาม / ข้อมูลต้นทาง</li>
      <li><span className="mr-1 inline-block size-2.5 rounded-sm bg-sand align-middle" />คอลัมน์ที่ pipeline คำนวณ</li>
      <li><span className={`mr-1 inline-block size-2.5 rounded-sm border align-middle ${resultTone[question]}`} />ผลที่แสดงบนหน้านี้ (สีประจำคำถาม)</li>
    </ul>
  );
}
