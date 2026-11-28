import { headers } from "next/headers";

export async function canViewHouseholdDetails() {
  if (process.env.NODE_ENV !== "development" || process.env.VERCEL) return false;
  const host = (await headers()).get("host");
  return host !== null && /^(?:localhost|127\.0\.0\.1)(?::\d+)?$/.test(host);
}
