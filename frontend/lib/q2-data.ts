import { fetchDashboardApi } from "./dashboard-api";

const incomes = ["lower", "middle", "upper", "unknown"] as const;
const cooling = ["no", "yes", "unknown"] as const;
const breakdowns = ["income", "cooling", "combined"] as const;
export const burdenKeys = ["high", "possibly_high", "low", "missing"] as const;

type Income = (typeof incomes)[number];
type Cooling = (typeof cooling)[number];
type Breakdown = (typeof breakdowns)[number];
export type BurdenKey = (typeof burdenKeys)[number];

export type Q2Row = Record<BurdenKey, number | null> & {
  breakdown: Breakdown;
  income: Income | "all";
  cooling: Cooling | "all";
  households: number | null;
};

type Q2Data = { status: "ready"; rows: Q2Row[] } | { status: "unconfigured" | "unavailable" };

const incomeLabels = { lower: "ไม่เกิน 10,000", middle: "10,001–20,000", upper: "มากกว่า 20,000", unknown: "ไม่ระบุรายได้", all: "ทุกช่วงรายได้" };
const coolingLabels = { no: "ไม่มีแอร์", yes: "มีแอร์", unknown: "ไม่ระบุการมีแอร์", all: "รวมทุกบ้าน" };

function parseRows(payload: unknown): Q2Row[] {
  if (!payload || typeof payload !== "object" || !("rows" in payload) || !Array.isArray(payload.rows) || payload.rows.length > 19) {
    throw new Error("Unexpected Q2 API response");
  }
  const seen = new Set<string>();
  return payload.rows.map((entry: unknown) => {
    if (!entry || typeof entry !== "object") throw new Error("Invalid Q2 row");
    const row = entry as Record<string, unknown>;
    const breakdown = breakdowns.find((id) => id === row.breakdown);
    const income = breakdown === "cooling" && row.income === "all" ? "all" : incomes.find((id) => id === row.income);
    const ac = breakdown === "income" && row.cooling === "all" ? "all" : cooling.find((id) => id === row.cooling);
    if (!breakdown || !income || !ac || (breakdown === "cooling") !== (income === "all") || (breakdown === "income") !== (ac === "all")) {
      throw new Error("Unexpected Q2 group");
    }
    const id = `${breakdown}/${income}/${ac}`;
    if (seen.has(id)) throw new Error("Duplicate Q2 group");
    seen.add(id);

    function count(key: BurdenKey | "households") {
      const value = row[key];
      if (value === null || (value === 0 && key !== "households")) return value;
      if (typeof value === "number" && Number.isSafeInteger(value) && value >= 5) return value;
      throw new Error("Invalid Q2 count");
    }

    const result: Q2Row = { breakdown, income, cooling: ac, households: count("households"), high: count("high"),
      possibly_high: count("possibly_high"), low: count("low"), missing: count("missing") };
    const counts = burdenKeys.map((key) => result[key]);
    if (!counts.every((value) => value === null) && (
      counts.some((value) => value === null) || counts.reduce<number>((sum, value) => sum + (value ?? 0), 0) !== result.households
    )) throw new Error("Invalid Q2 breakdown totals");
    return result;
  });
}

export function q2Endpoint() {
  const q3 = process.env.Q3_API_URL;
  return process.env.Q2_API_URL || (q3?.endsWith("/q3") ? q3.slice(0, -2) + "q2" : undefined);
}

export async function getQ2Data(): Promise<Q2Data> {
  const endpoint = q2Endpoint();
  if (!endpoint) return { status: "unconfigured" };
  try {
    return { status: "ready", rows: parseRows(await fetchDashboardApi(endpoint)) };
  } catch (error) {
    console.error("Q2 data unavailable", error instanceof Error ? error.name : "Error");
    return { status: "unavailable" };
  }
}

export function q2Groups(rows: Q2Row[], breakdown: Breakdown) {
  return rows.filter((row) => row.breakdown === breakdown).sort((a, b) =>
    incomes.findIndex((key) => key === a.income) - incomes.findIndex((key) => key === b.income) ||
    cooling.findIndex((key) => key === a.cooling) - cooling.findIndex((key) => key === b.cooling));
}

export function q2Label(row: Q2Row) {
  if (row.breakdown === "income") return incomeLabels[row.income];
  if (row.breakdown === "cooling") return coolingLabels[row.cooling];
  return `${incomeLabels[row.income]} · ${coolingLabels[row.cooling]}`;
}

export function q2Share(count: number | null, total: number | null) {
  return count === null || !total ? null : 100 * count / total;
}

export function q2Percent(value: number | null) {
  return value === null ? "—" : `${value.toFixed(1)}%`;
}
