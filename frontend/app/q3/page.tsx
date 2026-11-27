import type { Metadata } from "next";
import { DashboardHeading } from "../dashboard-ui";
import { Q3Section } from "../q3-section";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Q3 ลำดับความช่วยเหลือ | Bangkok Heat",
};

export default function Q3Page() {
  return (
    <>
      <DashboardHeading question="Q3" title="กลุ่มไหนควรได้รับความช่วยเหลือก่อน?"
        description="จัดกลุ่มตามการเผชิญความร้อนและความเปราะบาง · แบบสำรวจ Happy Home · คะแนนรุ่น D27/D28" />
      <Q3Section />
    </>
  );
}
