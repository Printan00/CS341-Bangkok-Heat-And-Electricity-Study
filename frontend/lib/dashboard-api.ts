import { Sha256 } from "@aws-crypto/sha256-js";
import { defaultProvider } from "@aws-sdk/credential-provider-node";
import { HttpRequest } from "@smithy/protocol-http";
import { SignatureV4 } from "@smithy/signature-v4";
import { awsCredentialsProvider } from "@vercel/oidc-aws-credentials-provider";

function dashboardCredentials() {
  if (!process.env.VERCEL) return defaultProvider();

  const roleArn = process.env.AWS_ROLE_ARN;
  if (!roleArn) throw new Error("AWS_ROLE_ARN is required for Vercel deployments");
  return awsCredentialsProvider({ roleArn });
}

export async function fetchDashboardApi(endpoint: string): Promise<unknown> {
  const url = new URL(endpoint);
  const region = url.hostname.match(/\.execute-api\.([a-z0-9-]+)\.amazonaws\.com$/)?.[1];
  if (!region || url.protocol !== "https:" || url.search || url.hash || url.port || url.username || url.password) {
    throw new Error("Invalid dashboard API URL");
  }
  const signer = new SignatureV4({
    credentials: dashboardCredentials(),
    region,
    service: "execute-api",
    sha256: Sha256,
  });
  const request = await signer.sign(new HttpRequest({
    protocol: url.protocol,
    hostname: url.hostname,
    method: "GET",
    path: url.pathname,
    headers: { host: url.host },
  }));
  const response = await fetch(url, {
    headers: request.headers,
    cache: "no-store",
    redirect: "error",
    signal: AbortSignal.timeout(26_000),
  });
  if (!response.ok) throw new Error(`Dashboard API returned ${response.status}`);
  return response.json();
}
