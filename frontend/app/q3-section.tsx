import Link from "next/link";
import { Suspense } from "react";
import { getQ3Data } from "../lib/q3-data";
import { Q3Table } from "./q3-table";
import { DashboardStatus } from "./dashboard-ui";

async function Q3Results() {
  const data = await getQ3Data();
  if (data.status !== "ready") {
    return (
      <DashboardStatus>
        {data.status === "unconfigured" ? "ยังไม่ได้ตั้งค่า API สำหรับข้อมูลจริง Q3" : "ดึงข้อมูลจริง Q3 ไม่สำเร็จ กรุณาลองใหม่ในภายหลัง"}
      </DashboardStatus>
    );
  }

  if (!data.rows.length) return <DashboardStatus>ยังไม่มีครัวเรือนที่จัดกลุ่มได้</DashboardStatus>;

  const priority = data.rows.find(({ group }) => group === "help_first");
  return (
    <>
      {priority?.households != null && (
        <p className="mb-3 rounded-panel bg-olive-soft p-3 text-sm"><strong className="text-olive">{priority.households} ครัวเรือนอยู่ในกลุ่มช่วยก่อน</strong> เพราะเผชิญความร้อนและมีความเปราะบางสูงตามเกณฑ์ของโครงการ</p>
      )}
      <Q3Table rows={data.rows} />
    </>
  );
}

export function Q3Section() {
  return (
    <section id="priority" aria-labelledby="priority-title">
      <h2 id="priority-title" className="mb-2 section-title">สรุปคะแนนเฉลี่ยตามกลุ่ม</h2>
      {process.env.NODE_ENV === "development" && process.env.Q3_INTERNAL_VIEW === "1" && (
        <Link className="mb-2 inline-block text-sm font-medium text-heat underline" href="/internal/q3" prefetch={false}>เปิดตารางรายครัวเรือนสำหรับตรวจข้อมูล</Link>
      )}
      <Suspense fallback={<DashboardStatus>กำลังโหลดผลสรุปจาก Athena</DashboardStatus>}>
        <Q3Results />
      </Suspense>
    </section>
  );
}
