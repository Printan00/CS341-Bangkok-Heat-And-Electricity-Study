import { DashboardHeading, DashboardStatus } from "../dashboard-ui";

export default function Q1Loading() {
  return (
    <>
      <DashboardHeading question="Q1" title="ลักษณะบ้านกับผลกระทบจากความร้อน"
        description="เปรียบเทียบครัวเรือนในแบบสำรวจ Happy Home" />
      <DashboardStatus>กำลังโหลดผลวิเคราะห์ Q1 จาก Athena</DashboardStatus>
    </>
  );
}
