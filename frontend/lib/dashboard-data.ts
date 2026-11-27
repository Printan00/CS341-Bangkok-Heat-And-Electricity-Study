export const communities = [
  { id: "all", label: "ทุกชุมชน" },
  { id: "a", label: "ชุมชน A (ตัวอย่าง)" },
  { id: "b", label: "ชุมชน B (ตัวอย่าง)" },
] as const;

export type Community = (typeof communities)[number]["id"];

const incomeLabels = [
  { label: "ไม่เกิน 10,000", detail: "บาท/เดือน" },
  { label: "10,001–20,000", detail: "บาท/เดือน" },
  { label: "มากกว่า 20,000", detail: "บาท/เดือน" },
] as const;

const housingLabels = ["ผนังไม้", "ผนังวัสดุอื่น", "ระบายอากาศไม่ดี", "ระบายอากาศดี"] as const;

type Count = readonly [affected: number, total: number];

type CommunitySample = {
  housing: readonly [Count, Count, Count, Count];
  income: readonly [Count, Count, Count];
};

const samples: Record<Exclude<Community, "all">, CommunitySample> = {
  a: { housing: [[14, 25], [9, 35], [17, 31], [6, 29]], income: [[18, 26], [6, 20], [2, 14]] },
  b: { housing: [[12, 25], [7, 35], [13, 30], [6, 30]], income: [[14, 29], [6, 12], [2, 19]] },
};

export function parseCommunity(value: string | string[] | undefined): Community {
  return communities.find(({ id }) => id === value)?.id ?? "all";
}

export function percent(affected: number, total: number) {
  return total ? Math.round((affected / total) * 100) : null;
}

function combineCounts(a: Count, b: Count, community: Community): Count {
  if (community === "all") return [a[0] + b[0], a[1] + b[1]];
  return community === "a" ? a : b;
}

export type Comparison = {
  label: string;
  detail?: string;
  count: Count;
  tone: "heat" | "sand" | "energy";
};

export type DashboardData = {
  housing: Comparison[];
  income: Comparison[];
  sampleSize: number;
  heatPercent: number | null;
  burdenPercent: number | null;
};

// Temporary comparison data for Q1 and Q2.
export async function getDashboardData(community: Community): Promise<DashboardData> {
  const housing = housingLabels.map((label, index): Comparison => ({
    label,
    count: combineCounts(samples.a.housing[index], samples.b.housing[index], community),
    tone: index % 2 === 0 ? "heat" : "sand",
  }));
  const income = incomeLabels.map((item, index): Comparison => ({
    ...item,
    count: combineCounts(samples.a.income[index], samples.b.income[index], community),
    tone: "energy",
  }));
  const [heatHouseholds, sampleSize] = housing.slice(0, 2).reduce<Count>(
    ([affected, total], { count }) => [affected + count[0], total + count[1]],
    [0, 0],
  );
  const highBurden = income.reduce((total, { count }) => total + count[0], 0);

  return { housing, income, sampleSize, heatPercent: percent(heatHouseholds, sampleSize), burdenPercent: percent(highBurden, sampleSize) };
}
