"use client";

import { useRef, useSyncExternalStore, useTransition } from "react";
import { useRouter } from "next/navigation";
import { ChevronDown, House, Info, ShieldCheck, Thermometer, X, Zap } from "lucide-react";
import { communities, type Community } from "../lib/dashboard-data";

const sections = [
  { id: "overview", label: "ภาพรวม", icon: House },
  { id: "heat", label: "ความร้อนในบ้าน", icon: Thermometer },
  { id: "electricity", label: "ภาระค่าไฟ", icon: Zap },
  { id: "priority", label: "ลำดับความช่วยเหลือ", icon: ShieldCheck },
] as const;

function subscribeToHash(callback: () => void) {
  window.addEventListener("hashchange", callback);
  return () => window.removeEventListener("hashchange", callback);
}

function currentHash() {
  return window.location.hash.slice(1) || "overview";
}

export function SectionNavigation() {
  const active = useSyncExternalStore(subscribeToHash, currentHash, () => "overview");

  return (
    <nav aria-label="ส่วนต่าง ๆ ของงานวิจัย">
      <ul className="flex flex-wrap gap-x-[5px] gap-y-[3px] desktop:grid desktop:gap-[3px]">
        {sections.map(({ id, label, icon: Icon }) => (
          <li key={id}>
            <a className="nav-link" href={`#${id}`} aria-current={active === id ? "location" : undefined}>
              <Icon className="size-4 shrink-0 desktop:size-[19px]" aria-hidden="true" />
              {label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

export function CommunityFilter({ community }: { community: Community }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  function changeCommunity(value: string) {
    const url = new URL(window.location.href);
    if (value === "all") url.searchParams.delete("community");
    else url.searchParams.set("community", value);
    startTransition(() => router.push(`${url.pathname}${url.search}${url.hash}`, { scroll: false }));
  }

  return (
    <div className="flex items-center gap-2 text-[13px] text-muted">
      <label htmlFor="community">ชุมชน</label>
      <div className="relative">
        <select className="min-h-[42px] w-[156px] appearance-none rounded-lg border border-[#dcd7ce] bg-white py-[5px] pr-[31px] pl-[11px] font-medium text-ink compact:min-h-[39px]" id="community" value={community} onChange={(event) => changeCommunity(event.target.value)} disabled={pending}>
          {communities.map(({ id, label }) => <option key={id} value={id}>{label}</option>)}
        </select>
        <ChevronDown className="pointer-events-none absolute top-[calc(50%-8px)] right-[11px]" size={17} aria-hidden="true" />
      </div>
      <span className="sr-only" role="status">{pending ? "กำลังอัปเดตข้อมูล" : `แสดงข้อมูล ${communities.find(({ id }) => id === community)?.label}`}</span>
    </div>
  );
}

export function Methodology() {
  const dialog = useRef<HTMLDialogElement>(null);

  return (
    <>
      <button type="button" className="toolbar-button" onClick={() => dialog.current?.showModal()}>
        <Info size={17} aria-hidden="true" />
        วิธีอ่านข้อมูล
      </button>
      <dialog ref={dialog} className="m-auto max-h-[calc(100dvh-32px)] w-[min(464px,calc(100vw-32px))] rounded-panel border border-line bg-white p-[22px] text-ink shadow-[0_16px_80px_#2d241828] backdrop:bg-[#27221e60]" aria-labelledby="guide-title">
        <div className="mb-[9px] flex items-center justify-between gap-3">
          <h2 id="guide-title" className="text-[25px] font-bold">วิธีอ่านข้อมูล</h2>
          <form method="dialog"><button className="toolbar-button size-10 p-0" aria-label="ปิดวิธีอ่านข้อมูล"><X size={21} aria-hidden="true" /></button></form>
        </div>
        <p className="text-muted">Q1 และ Q2 ใช้ข้อมูลจำลอง ส่วน Q3 ใช้ข้อมูลสรุปจาก Athena เมื่อเชื่อมต่อ API</p>
        <dl>
          <dt className="mt-[13px] font-semibold">ผลกระทบสูงจากความร้อน</dt>
          <dd className="text-muted">สัดส่วนครัวเรือนที่อยู่ในกลุ่มผลกระทบสูง คำนวณแยกตามลักษณะบ้านแต่ละกลุ่ม</dd>
          <dt className="mt-[13px] font-semibold">ภาระค่าไฟสูง</dt>
          <dd className="text-muted">ค่าไฟหน้าร้อนคิดเป็นอย่างน้อย 10% ของรายได้ต่อเดือนตามเกณฑ์ตัวอย่าง</dd>
          <dt className="mt-[13px] font-semibold">ลำดับความช่วยเหลือ</dt>
          <dd className="text-muted">กลุ่มช่วยก่อนมีคะแนนการเผชิญความร้อนและความเปราะบางอย่างน้อย 0.5 ทั้งสองแกน ตัวเลขแสดงเฉพาะระดับกลุ่ม</dd>
        </dl>
      </dialog>
    </>
  );
}
