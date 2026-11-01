// SPDX-License-Identifier: MPL-2.0
// Who the browser signs in as (ADR-A149 decision 8). The service describes its authenticator at /api/session. With
// `local`, the browser names one of the developer principals it offers in X-Lattice-Principal. With `oidc`, it signs in
// at the provider by the authorization code flow with PKCE (RFC 7636) and sends the access token as a bearer token.

export interface Session {
  provider: "local" | "oidc";
  principal?: string;
  admin?: boolean;
  principalOption?: string[];
  administrator?: string[];
  issuer?: string;
  clientId?: string;
  scope?: string;
  authorizationEndpoint?: string;
  tokenEndpoint?: string;
}

const LOCAL = "lattice-studio:principal";
const TOKEN = "lattice-studio:token";
const PENDING = "lattice-studio:sign-in";

function read(storage: () => Storage, key: string): string | undefined {
  try {
    return storage().getItem(key) ?? undefined;
  } catch {
    return undefined;
  }
}

function write(storage: () => Storage, key: string, value?: string): void {
  try {
    if (value === undefined) storage().removeItem(key);
    else storage().setItem(key, value);
  } catch {
    // Storage refused, as in a private window, so the choice lasts only for this page.
  }
}

const local = () => localStorage;
// A token lives as long as the tab, never across a browser restart.
const tab = () => sessionStorage;

/** The headers that say who a request is from. */
export function authHeaders(): Record<string, string> {
  const token = read(tab, TOKEN);
  if (token) return { Authorization: `Bearer ${token}` };
  const name = read(local, LOCAL);
  return name ? { "X-Lattice-Principal": name } : {};
}

export async function loadSession(): Promise<Session> {
  const response = await fetch("/api/session", { headers: authHeaders() });
  if (!response.ok) throw new Error(`The service's session answered ${response.status}`);
  return (await response.json()) as Session;
}

/** Signs in locally as `name`, one of the session's principal options. */
export function chooseLocal(name: string): void {
  write(local, LOCAL, name);
  location.reload();
}

function base64url(bytes: Uint8Array): string {
  return btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function redirectUri(): string {
  return location.origin + location.pathname;
}

/** Goes to the provider to sign in, remembering where to come back to. */
export async function signIn(session: Session): Promise<void> {
  if (!session.authorizationEndpoint || !session.clientId) throw new Error("The service names no provider to sign in at.");
  const verifier = base64url(crypto.getRandomValues(new Uint8Array(32)));
  const state = base64url(crypto.getRandomValues(new Uint8Array(16)));
  const challenge = base64url(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier))));
  write(tab, PENDING, JSON.stringify({ verifier, state, hash: location.hash }));
  const url = new URL(session.authorizationEndpoint);
  url.search = new URLSearchParams({
    response_type: "code",
    client_id: session.clientId,
    redirect_uri: redirectUri(),
    scope: session.scope ?? "openid",
    state,
    code_challenge: challenge,
    code_challenge_method: "S256",
  }).toString();
  location.assign(url.toString());
}

/** On the way back from the provider, exchanges its code for a token. True when it did. */
export async function completeSignIn(session: Session): Promise<boolean> {
  const params = new URLSearchParams(location.search);
  const code = params.get("code");
  const pending = read(tab, PENDING);
  if (!code || !pending || !session.tokenEndpoint || !session.clientId) return false;
  const { verifier, state, hash } = JSON.parse(pending) as { verifier: string; state: string; hash: string };
  write(tab, PENDING);
  history.replaceState(null, "", redirectUri() + (hash ?? ""));
  if (params.get("state") !== state) throw new Error("The provider's answer does not match this sign-in.");
  const response = await fetch(session.tokenEndpoint, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ grant_type: "authorization_code", code, redirect_uri: redirectUri(), client_id: session.clientId, code_verifier: verifier }),
  });
  if (!response.ok) throw new Error(`The provider refused the sign-in (${response.status}).`);
  const token = ((await response.json()) as { access_token?: string }).access_token;
  if (!token) throw new Error("The provider gave no access token.");
  write(tab, TOKEN, token);
  return true;
}

export function signOut(): void {
  write(tab, TOKEN);
  write(local, LOCAL);
  location.reload();
}
