import { fetchDashboardApi } from "./dashboard-api";

const groups = ["help_first", "watch", "lower_exposure"] as const;

export type RiskGroup = (typeof groups)[number];
export type RiskMetric = "risk_score" | "exposure" | "vulnerability" | "heat" | "housing" | "finance" | "burden" | "coping";
export type RiskRow = Record<RiskMetric, number | null> & {
  group: RiskGroup;
  households: number | null;
  suppressed: boolean;
};

type Q3Data =
  | { status: "ready"; rows: RiskRow[] }
  | { status: "unconfigured" | "unavailable" };

function parseQ3(payload: unknown): RiskRow[] {
  if (!payload || typeof payload !== "object" || !("rows" in payload) || !Array.isArray(payload.rows)) {
    throw new Error("Unexpected Q3 API response");
  }

  if (payload.rows.length > groups.length) throw new Error("Too many Q3 groups");
  const seen = new Set<RiskGroup>();
  return payload.rows.map((entry) => {
    if (!entry || typeof entry !== "object") throw new Error("Invalid Q3 group");
    const group = groups.find((id) => id === entry.group);
    const households = entry.households;
    const suppressed = entry.suppressed;
    if (!group || seen.has(group) || typeof suppressed !== "boolean" ||
        (suppressed ? households !== null : !Number.isSafeInteger(households) || households < 5)) {
      throw new Error("Invalid Q3 disclosure status");
    }
    seen.add(group);

    function readMetric(key: RiskMetric): number | null {
      const value: unknown = entry[key];
      if (value === null) return null;
      if (!suppressed && typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 100) return value;
      throw new Error("Invalid Q3 metric");
    }

    return {
      group, households, suppressed,
      risk_score: readMetric("risk_score"),
      exposure: readMetric("exposure"),
      vulnerability: readMetric("vulnerability"),
      heat: readMetric("heat"),
      housing: readMetric("housing"),
      finance: readMetric("finance"),
      burden: readMetric("burden"),
      coping: readMetric("coping"),
    };
  });
}

export async function getQ3Data(): Promise<Q3Data> {
  const endpoint = process.env.Q3_API_URL;
  if (!endpoint) return { status: "unconfigured" };

  try {
    return { status: "ready", rows: parseQ3(await fetchQ3(endpoint)) };
  } catch (error) {
    console.error("Q3 data unavailable", error instanceof Error ? error.name : "Error");
    return { status: "unavailable" };
  }
}

export async function fetchQ3(endpoint: string, households = false): Promise<unknown> {
  if (!households) return fetchDashboardApi(endpoint);
  const url = new URL(endpoint);
  url.pathname = url.pathname.replace(/\/$/, "") + "/households";
  return fetchDashboardApi(url.href);
}
