import { fetchDashboardApi } from "./dashboard-api";

const kinds = ["comparison", "heatmap", "housing", "distribution", "feature_detail", "community", "profile"] as const;
export type Q1Kind = (typeof kinds)[number];
export type Q1Row = {
  kind: Q1Kind;
  dimension: string;
  label: string;
  households: number | null;
  high: number | null;
  low: number | null;
  medium: number | null;
  value: number | null;
  suppressed: boolean;
};
export type Q1Results = { rows: Q1Row[]; pValues: Record<string, number> };
type Q1Data = { status: "ready"; data: Q1Results } | { status: "unconfigured" | "unavailable" };

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function readResult(payload: unknown): Q1Results {
  if (!isRecord(payload) || !Array.isArray(payload.rows) || !isRecord(payload.pValues)) {
    throw new Error("Unexpected Q1 response");
  }
  const rows = payload.rows.map((row: unknown): Q1Row => {
    if (!isRecord(row)) throw new Error("Invalid Q1 row");
    const { dimension, label, suppressed } = row;
    const kind = kinds.find((candidate) => candidate === row.kind);
    if (!kind || typeof dimension !== "string" || typeof label !== "string" || typeof suppressed !== "boolean") {
      throw new Error("Invalid Q1 category");
    }
    const readNumber = (field: "households" | "high" | "low" | "medium" | "value") => {
      const value = row[field];
      if (value === null) return null;
      if (!suppressed && typeof value === "number" && Number.isFinite(value) && value >= 0) return value;
      throw new Error("Invalid Q1 value");
    };
    return { kind, dimension, label, suppressed, households: readNumber("households"), high: readNumber("high"), low: readNumber("low"), medium: readNumber("medium"), value: readNumber("value") };
  });
  const pValues = Object.fromEntries(Object.entries(payload.pValues).filter(
    (entry): entry is [string, number] => typeof entry[1] === "number" && entry[1] >= 0 && entry[1] <= 1,
  ));
  return { rows, pValues };
}

export async function getQ1Data(): Promise<Q1Data> {
  const q3Endpoint = process.env.Q3_API_URL;
  const endpoint = process.env.Q1_API_URL ||
    (q3Endpoint?.endsWith("/q3") ? q3Endpoint.slice(0, -2) + "q1" : undefined);
  if (!endpoint) return { status: "unconfigured" };
  try {
    return { status: "ready", data: readResult(await fetchDashboardApi(endpoint)) };
  } catch (error) {
    console.error("Q1 data unavailable", error instanceof Error ? error.name : "Error");
    return { status: "unavailable" };
  }
}

export function wallComparison(rows: Q1Row[]) {
  const wall = rows.filter(({ kind, dimension }) => kind === "comparison" && dimension === "wall");
  const wood = wall.find(({ label }) => label === "wood");
  const other = wall.find(({ label }) => label === "other");
  return wood?.value != null && other?.value != null ?
    { wood: { ...wood, value: wood.value }, other: { ...other, value: other.value } } : null;
}
