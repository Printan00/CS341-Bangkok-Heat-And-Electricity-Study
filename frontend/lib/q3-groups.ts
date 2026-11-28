import type { RiskGroup } from "./q3-data";

export const groupInfo: Record<RiskGroup, { order: number; label: string }> = {
  help_first: { order: 1, label: "ช่วยก่อน" },
  watch: { order: 2, label: "เฝ้าระวัง" },
  lower_exposure: { order: 3, label: "เผชิญความร้อนต่ำกว่าเกณฑ์" },
};
