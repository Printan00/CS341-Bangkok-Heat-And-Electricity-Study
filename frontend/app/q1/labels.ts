import type { Q1Row } from "../../lib/q1-data";

export const levels = [
  { key: "low", label: "ต่ำ", range: "0–4", color: "bg-[#ead7b7]", text: "text-ink" },
  { key: "medium", label: "ปานกลาง", range: "5–7", color: "bg-[#eeaa83]", text: "text-ink" },
  { key: "high", label: "สูง", range: "8–13", color: "bg-heat", text: "text-white" },
] as const;

export const housingFeatures: Record<string, { label: string; groups: Record<string, string> }> = {
  housing_type: { label: "ประเภทที่อยู่", groups: { single: "บ้านเดี่ยว", rowhouse: "บ้านแถว / ทาวน์เฮาส์", other: "ห้องเช่า / แฟลต / ที่อยู่อาศัยอื่น" } },
  wall: { label: "วัสดุผนัง", groups: { wood: "ผนังไม้", concrete: "ผนังคอนกรีต", other: "ผนังผสม / วัสดุอื่น / ไม่ระบุ" } },
  roof: { label: "หลังคา", groups: { metal: "สังกะสี / เมทัลชีท", other: "หลังคาวัสดุอื่น / ไม่ระบุ" } },
  ceiling: { label: "ฝ้าเพดาน", groups: { absent: "ไม่มีฝ้า", other: "มีฝ้า / ไม่แน่ใจ" } },
  insulation: { label: "ฉนวน", groups: { absent: "ไม่มีฉนวน", other: "มีฉนวน / ไม่แน่ใจ" } },
  ventilation: { label: "ระบายอากาศ", groups: { good: "ระบายอากาศดี", moderate: "ระบายอากาศปานกลาง", poor: "ระบายอากาศไม่ดี" } },
  shade: { label: "ร่มเงา", groups: { none: "ไม่มีเลย", little: "ร่มเงาน้อย", moderate: "พอมีร่มเงา", substantial: "ร่มเงามาก" } },
};

const profileLabels: Record<string, Record<string, string>> = {
  coping: { limited: "รับมือได้จำกัด", not_limited: "รับมือได้ไม่จำกัด" },
  housing_risk: { "0-2": "คะแนนสภาพบ้าน 0–2", "3-5": "คะแนนสภาพบ้าน 3–5" },
};

export const analysisLabels: Record<Q1Row["kind"], string> = {
  comparison: "สัดส่วนผลกระทบสูงตามลักษณะบ้าน",
  heatmap: "ผนัง × การระบายอากาศ",
  housing: "คะแนนสภาพบ้าน",
  distribution: "ผลกระทบทั้งกลุ่มตัวอย่าง",
  feature_detail: "คะแนนเฉลี่ยตามลักษณะบ้าน",
  community: "ชุมชน",
  profile: "ระดับผลกระทบตามบริบท",
};

export function groupLabel(row: Q1Row): string {
  const { kind, dimension, label } = row;
  if (label === "unknown") return kind === "community" ? "ไม่ทราบชุมชน" : "ไม่ระบุ / ไม่แน่ใจ";
  if (kind === "distribution") return levels.find(({ key }) => key === label)?.label ?? label;
  if (kind === "heatmap") return `${label === "wood" ? "ผนังไม้" : "ผนังวัสดุอื่น"} · ${housingFeatures.ventilation.groups[dimension] ?? "การระบายอากาศไม่ระบุ"}`;
  if (kind === "housing") return `คะแนนสภาพบ้าน ${label.replace("-", "–")}`;
  if (kind === "profile") return profileLabels[dimension]?.[label] ?? label;
  if (kind === "comparison" || kind === "feature_detail") {
    if (kind === "comparison" && dimension === "wall" && label === "other") return "ผนังวัสดุอื่นทั้งหมด";
    if (kind === "comparison" && dimension === "ventilation" && label === "other") return "ระบายอากาศปานกลาง / ดี / อื่น ๆ";
    return housingFeatures[dimension]?.groups[label] ?? label;
  }
  return label;
}
