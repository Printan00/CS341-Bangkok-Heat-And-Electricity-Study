import { BookOpenCheck, ChevronDown } from "lucide-react";
import type { ReactNode } from "react";
import { FlowLegend } from "./method-flow";

type Question = "Q1" | "Q2" | "Q3";

const tones: Record<Question, { text: string; soft: string; border: string }> = {
  Q1: { text: "text-heat", soft: "bg-heat-soft", border: "border-heat/30" },
  Q2: { text: "text-energy", soft: "bg-energy-soft", border: "border-energy/30" },
  Q3: { text: "text-olive", soft: "bg-olive-soft", border: "border-olive/30" },
};

/** Bottom-of-page section explaining how a question's numbers are computed. */
export function MethodSection({ question, lead, source, flow, children }: {
  question: Question;
  lead: ReactNode;
  source: { table: string; rows: string; columns: string[] };
  flow: ReactNode;
  children: ReactNode;
}) {
  const tone = tones[question];
  const id = `${question.toLowerCase()}-method`;
  return (
    <section id={id} className="mt-8 scroll-mt-4 border-t border-line pt-5" aria-labelledby={`${id}-title`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className={`grid size-8 place-items-center rounded-lg ${tone.soft} ${tone.text}`}><BookOpenCheck size={17} aria-hidden="true" /></span>
        <h2 id={`${id}-title`} className="section-title">วิธีคำนวณและที่มาของตัวเลข</h2>
      </div>
      <p className="mt-2 max-w-3xl text-sm text-muted">{lead}</p>

      <div className="mt-4 grid gap-3">
        <div className="panel min-w-0 p-4">
          <h3 className="text-sm font-bold">ข้อมูลที่ใช้</h3>
          <dl className="mt-2 space-y-1.5 text-sm">
            <div className="flex flex-wrap gap-x-2"><dt className="text-muted">ตาราง</dt><dd><Col>{source.table}</Col></dd></div>
            <div className="flex flex-wrap gap-x-2"><dt className="text-muted">แถว</dt><dd>{source.rows}</dd></div>
          </dl>
          <p className="mt-2 text-xs text-muted">คอลัมน์</p>
          <ul className="mt-1 flex flex-wrap gap-1">
            {source.columns.map((column) => <li key={column}><Col>{column}</Col></li>)}
          </ul>
        </div>
        <div className="panel min-w-0 p-4">
          <h3 className="text-sm font-bold">เส้นทางการคำนวณ</h3>
          <div className="mt-3 space-y-5">{flow}</div>
          <FlowLegend question={question} />
        </div>
      </div>

      <div className="panel mt-3 divide-y divide-line overflow-hidden">{children}</div>
    </section>
  );
}

/** One collapsible topic inside MethodSection. */
export function MethodStep({ question, n, title, hint, open, children }: {
  question: Question; n: number; title: string; hint?: string; open?: boolean; children: ReactNode;
}) {
  const tone = tones[question];
  return (
    <details className="group" open={open}>
      <summary className="flex cursor-pointer list-none items-center gap-3 px-4 py-3 hover:bg-canvas [&::-webkit-details-marker]:hidden">
        <span className={`grid size-6 shrink-0 place-items-center rounded-md text-xs font-bold tabular-nums ${tone.soft} ${tone.text}`}>{n}</span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-semibold compact:text-[15px]">{title}</span>
          {hint && <span className="block text-xs text-muted">{hint}</span>}
        </span>
        <ChevronDown size={17} className="shrink-0 text-muted transition-transform group-open:rotate-180 motion-reduce:transition-none" aria-hidden="true" />
      </summary>
      <div className="space-y-3 px-4 pb-4 text-sm leading-relaxed compact:pl-[3.25rem]">{children}</div>
    </details>
  );
}

export function Col({ children }: { children: ReactNode }) {
  return <code className="rounded bg-sand px-1 py-px font-mono text-[12px] text-ink">{children}</code>;
}

export function Formula({ children }: { children: string }) {
  return <pre className="mt-2 overflow-x-auto rounded-lg bg-sand px-3 py-2.5 font-mono text-[12.5px] leading-relaxed whitespace-pre text-ink">{children}</pre>;
}

/** Worked example using the hypothetical household (not real data). */
export function Example({ children }: { children: ReactNode }) {
  return (
    <p className="rounded-lg border border-dashed border-line bg-canvas px-3 py-2 text-[13px]">
      <strong className="mr-1.5 text-ink">ตัวอย่างบ้านสมมติ</strong>{children}
    </p>
  );
}

/** Where a rule comes from: published work or a team decision (D-code). */
export function Basis({ kind, children }: { kind: "ref" | "team" | "method"; children: ReactNode }) {
  const label = kind === "ref" ? "มีงานอ้างอิง" : kind === "team" ? "ทีมกำหนดเอง" : "วิธีมาตรฐาน";
  const style = kind === "ref" ? "bg-energy-soft text-energy" : kind === "team" ? "bg-sand text-muted" : "bg-olive-soft text-olive";
  return (
    <p className="text-[13px] text-muted">
      <span className={`mr-1.5 inline-block rounded px-1.5 py-px text-[11px] font-bold ${style}`}>{label}</span>{children}
    </p>
  );
}

export function Caution({ children }: { children: ReactNode }) {
  return <p className="border-l-2 border-heat/40 pl-3 text-[13px] text-muted"><strong className="text-ink">อ่านอย่างระวัง</strong> {children}</p>;
}

/** Small lookup table, e.g. answer → score. */
export function MiniTable({ head, rows, caption }: { head: string[]; rows: ReactNode[][]; caption: string }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-line">
      <table className="w-full min-w-[26rem] text-left text-[13px]">
        <caption className="sr-only">{caption}</caption>
        <thead className="bg-sand"><tr>{head.map((h) => <th key={h} scope="col" className="px-2.5 py-1.5 font-semibold">{h}</th>)}</tr></thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t border-line align-top">
              {row.map((cell, j) => <td key={j} className="px-2.5 py-1.5">{cell}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export const references = {
  ipcc: { label: "IPCC AR5 WGII, Annex II Glossary", href: "https://www.ipcc.ch/site/assets/uploads/2018/02/WGIIAR5-AnnexII_FINAL.pdf" },
  oecd: { label: "OECD/JRC Handbook on Constructing Composite Indicators (2008)", href: "https://publications.jrc.ec.europa.eu/repository/handle/JRC47008" },
  aceee: { label: "Drehobl, Ross & Ayala (2020), ACEEE", href: "https://www.aceee.org/sites/default/files/publications/researchreports/u2006.pdf" },
  boardman: { label: "นิยาม fuel poverty ของ Boardman (1991) สรุปโดยรัฐบาลสก็อตแลนด์", href: "https://gov.scot/publications/new-definition-fuel-poverty-scotland-review-recent-evidence/pages/4" },
};

export function Ref({ id }: { id: keyof typeof references }) {
  const ref = references[id];
  return <a href={ref.href} target="_blank" rel="noreferrer" className="font-medium text-energy underline underline-offset-2">{ref.label}</a>;
}
