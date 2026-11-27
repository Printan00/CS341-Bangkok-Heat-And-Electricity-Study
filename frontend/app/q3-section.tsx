import { ShieldCheck } from "lucide-react";
import Link from "next/link";
import { Suspense } from "react";
import { getQ3Data } from "../lib/q3-data";
import { Q3Table } from "./q3-table";

async function Q3Results() {
  const data = await getQ3Data();
  if (data.status !== "ready") {
    return (
      <p className="panel p-3 text-sm text-muted">
        {data.status === "unconfigured" ? "ยังไม่ได้ตั้งค่า API สำหรับข้อมูลจริง Q3" : "ดึงข้อมูลจริง Q3 ไม่สำเร็จ กรุณาลองใหม่ในภายหลัง"}
      </p>
    );
  }

  if (!data.rows.length) return <p className="panel p-3 text-sm text-muted">ยังไม่มีครัวเรือนที่จัดกลุ่มได้</p>;

  const priority = data.rows.find(({ group }) => group === "help_first");
  return (
    <>
      {priority?.households != null && (
        <p className="mb-2 text-sm"><strong className="text-heat">{priority.households} ครัวเรือนอยู่ในกลุ่มช่วยก่อน</strong> เพราะเผชิญความร้อนและมีความเปราะบางสูงตามเกณฑ์ของโครงการ</p>
      )}
      <Q3Table rows={data.rows} />
    </>
  );
}

export function Q3Section() {
  return (
    <section className="mt-4" id="priority" aria-labelledby="priority-title">
      <div className="mb-2 flex items-center gap-2">
        <span className="question-icon bg-olive-soft text-olive"><ShieldCheck size={16} aria-hidden="true" /> Q3</span>
        <h2 id="priority-title" className="section-title">กลุ่มไหนควรได้รับความช่วยเหลือก่อน?</h2>
      </div>
      <p className="mb-2 text-xs text-muted">ข้อมูลรวมจาก Happy Home · คะแนนรุ่น D27/D28 · รวมทุกชุมชน</p>
      {process.env.NODE_ENV === "development" && process.env.Q3_INTERNAL_VIEW === "1" && (
        <Link className="mb-2 inline-block text-sm font-medium text-heat underline" href="/internal/q3" prefetch={false}>เปิดตารางรายครัวเรือนสำหรับตรวจข้อมูล</Link>
      )}
      <Suspense fallback={<p className="panel p-3 text-sm text-muted" role="status">กำลังโหลดผลสรุปจาก Athena</p>}>
        <Q3Results />
      </Suspense>
    </section>
  );
}
