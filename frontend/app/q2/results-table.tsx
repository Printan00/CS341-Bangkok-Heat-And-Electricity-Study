import { burdenKeys, q2Label, q2Percent, q2Share, type Q2Row } from "../../lib/q2-data";
import { burdenLabels } from "./figures";

export function Q2ResultsTable({ id, title, rows }: { id: string; title: string; rows: Q2Row[] }) {
  const allHidden = rows.length > 0 && rows.every((row) => burdenKeys.every((key) => row[key] === null));
  return (
    <section aria-labelledby={id}>
      <h3 id={id} className="mb-2 text-sm font-bold">{title}</h3>
      <div className="panel overflow-x-auto" role="region" aria-labelledby={id} tabIndex={0}>
        <table className="w-full min-w-[560px] border-collapse text-sm" aria-labelledby={id}>
          <thead className="bg-sand text-xs text-muted">
            <tr>
              <th scope="col" className="px-3 py-2 text-left">กลุ่มครัวเรือน</th>
              <th scope="col" className="px-3 py-2 text-right">บ้านทั้งหมด</th>
              {burdenKeys.map((key) => <th key={key} scope="col" className="px-3 py-2 text-right">{burdenLabels[key]}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={q2Label(row)} className="border-t border-line">
                <th scope="row" className="px-3 py-2 text-left font-semibold">{q2Label(row)}</th>
                <td className="px-3 py-2 text-right tabular-nums">{row.households ?? "—"}</td>
                {allHidden ? index === 0 && (
                  <td colSpan={burdenKeys.length} rowSpan={rows.length} className="border-l border-line bg-canvas px-4 py-3 text-center align-middle text-xs text-muted">
                    <strong className="block text-sm text-ink">ปกปิดระดับภาระของตารางนี้ทั้งชุด</strong>
                    บางกลุ่มย่อยมีบ้านน้อยกว่า 5 หลัง ถ้าแสดงบางช่อง จะคำนวณย้อนหาช่องที่ปกปิดได้ จึงแสดงเฉพาะจำนวนบ้านในแต่ละกลุ่ม
                  </td>
                ) : burdenKeys.map((key) => (
                  <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums" key={key}>
                    {row[key] === null ? "—" : <>{row[key]} <span className="text-xs text-muted">({q2Percent(q2Share(row[key], row.households))})</span></>}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
