import { ArrowRight, ShieldCheck, Thermometer, Zap } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

const questions = {
  Q1: { icon: Thermometer, tone: "bg-heat-soft text-heat", foreground: "text-heat" },
  Q2: { icon: Zap, tone: "bg-energy-soft text-energy", foreground: "text-energy" },
  Q3: { icon: ShieldCheck, tone: "bg-olive-soft text-olive", foreground: "text-olive" },
};

type Question = keyof typeof questions;

function QuestionLabel({ question }: { question: Question }) {
  const { icon: Icon, tone } = questions[question];
  return <span className={`question-icon ${tone}`}><Icon size={15} aria-hidden="true" />{question}</span>;
}

export function DashboardHeading({ title, description, question }: { title: string; description: string; question?: Question }) {
  return (
    <div className="py-4 compact:pt-5">
      <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1">
        {question && <QuestionLabel question={question} />}
        <h1 className="text-[clamp(24px,3.3cqi,36px)] leading-tight font-bold text-pretty">{title}</h1>
      </div>
      <p className="mt-1.5 max-w-3xl text-sm text-muted">{description}</p>
    </div>
  );
}

export function DashboardCardTitle({ id, title, question }: { id: string; title: string; question: Question }) {
  return (
    <header className="flex flex-wrap items-start gap-x-2.5 gap-y-1">
      <QuestionLabel question={question} />
      <h2 id={id} className="min-w-0 flex-1 text-base leading-snug font-bold compact:text-lg">{title}</h2>
    </header>
  );
}

export function DashboardDetailLink({ question }: { question: Question }) {
  const href = question === "Q1" ? "/q1" : question === "Q2" ? "/q2" : "/q3";
  return (
    <Link href={href} prefetch={false} className={`inline-flex min-h-9 w-fit items-center gap-1.5 text-sm font-semibold underline-offset-4 hover:underline ${questions[question].foreground}`}>
      ดูรายละเอียด {question}<ArrowRight size={15} aria-hidden="true" />
    </Link>
  );
}

export function DashboardStatus({ children }: { children: ReactNode }) {
  return <p className="panel p-4 text-sm text-muted" role="status">{children}</p>;
}
