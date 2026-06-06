// Emergent-managed Google OAuth helper.
// Mobile: opens WebBrowser.openAuthSessionAsync, reads session_id from result.url.
// Web: redirects window.location to auth URL; after redirect /auth route picks
// up the session_id from URL hash/query and exchanges it.
import { Platform, Linking } from "react-native";
import * as WebBrowser from "expo-web-browser";
import * as LinkingExpo from "expo-linking";

const EMERGENT_AUTH_BASE = "https://auth.emergentagent.com";
const SESSION_DATA_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data";

export function getRedirectUrl(): string {
  if (Platform.OS === "web") {
    return typeof window !== "undefined" ? window.location.origin + "/auth" : "";
  }
  return LinkingExpo.createURL("auth");
}

export function buildAuthUrl(redirectUrl: string): string {
  return `${EMERGENT_AUTH_BASE}/?redirect=${encodeURIComponent(redirectUrl)}`;
}

/** Mobile flow: open WebBrowser and return the session_id if user completes auth. */
export async function startGoogleAuthMobile(): Promise<string | null> {
  const redirectUrl = getRedirectUrl();
  const authUrl = buildAuthUrl(redirectUrl);

  const result = await WebBrowser.openAuthSessionAsync(authUrl, redirectUrl);
  if (result.type !== "success" || !result.url) return null;

  return parseSessionId(result.url);
}

/** Web flow: full-page redirect. The /auth route handles the return trip. */
export function startGoogleAuthWeb() {
  if (typeof window === "undefined") return;
  const redirectUrl = getRedirectUrl();
  window.location.href = buildAuthUrl(redirectUrl);
}

export function parseSessionId(url: string): string | null {
  try {
    // Match `#session_id=...` or `?session_id=...`
    const m = url.match(/[?#]session_id=([^&]+)/);
    return m ? decodeURIComponent(m[1]) : null;
  } catch {
    return null;
  }
}

export async function exchangeSessionIdForToken(sessionId: string) {
  const r = await fetch(SESSION_DATA_URL, {
    method: "GET",
    headers: { "X-Session-ID": sessionId },
  });
  if (!r.ok) throw new Error(`Google session validation failed (${r.status})`);
  const data = await r.json();
  // Returns { id, email, name, picture, session_token }
  return data as {
    id: string;
    email: string;
    name?: string;
    picture?: string;
    session_token: string;
  };
}
