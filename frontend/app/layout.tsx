import type { Metadata } from "next";
import "@fontsource/poppins/latin-400.css";
import "@fontsource/poppins/latin-500.css";
import "@fontsource/poppins/latin-600.css";
import "@fontsource/poppins/latin-700.css";
import "@fontsource/ibm-plex-sans-thai/thai-400.css";
import "@fontsource/ibm-plex-sans-thai/thai-500.css";
import "@fontsource/ibm-plex-sans-thai/thai-600.css";
import "@fontsource/ibm-plex-sans-thai/thai-700.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "ความร้อนและค่าไฟในกรุงเทพฯ | Bangkok Heat",
  description: "แดชบอร์ดงานวิจัยเรื่องผลกระทบของความร้อนและภาระค่าไฟในครัวเรือนกรุงเทพฯ",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="th">
      <body>{children}</body>
    </html>
  );
}
