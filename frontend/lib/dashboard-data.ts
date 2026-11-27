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


type Count = readonly [affected: number, total: number];

type CommunitySample = {
  income: readonly [Count, Count, Count];
};

const samples: Record<Exclude<Community, "all">, CommunitySample> = {
  a: { income: [[18, 26], [6, 20], [2, 14]] },
  b: { income: [[14, 29], [6, 12], [2, 19]] },
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
};

export type DashboardData = {
  income: Comparison[];
  sampleSize: number;
  burdenPercent: number | null;
};

// Temporary comparison data for Q2.
export async function getDashboardData(community: Community): Promise<DashboardData> {
  const income = incomeLabels.map((item, index): Comparison => ({
    ...item,
    count: combineCounts(samples.a.income[index], samples.b.income[index], community),
  }));
  const [highBurden, sampleSize] = income.reduce<Count>(
    ([affected, total], { count }) => [affected + count[0], total + count[1]],
    [0, 0],
  );
  return { income, sampleSize, burdenPercent: percent(highBurden, sampleSize) };
}
