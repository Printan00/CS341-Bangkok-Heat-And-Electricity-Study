import Link from "next/link";
import type { ReactNode } from "react";
import { DashboardBreadcrumb, Methodology, SectionNavigation } from "./controls";

export function DashboardShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-dvh desktop:grid desktop:grid-cols-[178px_minmax(0,1fr)] wide:grid-cols-[192px_minmax(0,1fr)]">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-20 focus:rounded-lg focus:bg-white focus:px-3.5 focus:py-2">ข้ามไปยังเนื้อหา</a>
      <aside className="border-b border-line bg-white px-3 py-2.5 compact:px-5 desktop:sticky desktop:top-0 desktop:h-dvh desktop:self-start desktop:overflow-y-auto desktop:border-r desktop:border-b-0 desktop:px-3 desktop:py-4 wide:px-4">
        <Link href="/" lang="en" className="flex min-h-9 flex-col justify-center leading-tight desktop:border-b desktop:border-line desktop:px-2 desktop:pb-3">
          <strong className="text-base font-bold tracking-[-.035em]">Bangkok Heat</strong>
          <span className="mt-1 text-[9px] font-semibold tracking-[.13em] text-muted uppercase">Electricity Study</span>
        </Link>
        <div className="mt-2.5 desktop:mt-3">
          <p className="mx-2 mb-1 hidden text-[13px] font-semibold text-muted desktop:block">งานวิจัย</p>
          <SectionNavigation />
        </div>
      </aside>

      <div className="@container mx-auto w-full min-w-0 max-w-[1340px] px-3 compact:px-5 wide:px-7">
        <header className="flex min-h-12 items-center justify-between gap-2 border-b border-line">
          <DashboardBreadcrumb />
          <Methodology />
        </header>
        <main id="main-content" tabIndex={-1} className="min-w-0 pb-5">
          {children}
        </main>
        <footer className="flex flex-wrap justify-between gap-x-4 gap-y-1 border-t border-line py-3 text-xs text-muted">
          <span lang="en">Bangkok Heat and Electricity Study</span>
          <span>โครงการศึกษาความร้อนและค่าไฟในกรุงเทพฯ</span>
        </footer>
      </div>
    </div>
  );
}
