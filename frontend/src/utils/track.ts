// Lightweight, anonymous page-view tracker.
// Fires fire-and-forget; never blocks UI or shows errors.
import { Platform } from "react-native";
import { BACKEND_URL } from "@/src/api";

let lastPath = "";

export function trackPageview(path: string) {
  if (!path || path === lastPath) return;
  lastPath = path;
  try {
    const referrer = Platform.OS === "web" && typeof document !== "undefined" ? document.referrer : "";
    // Don't await; never throw.
    fetch(`${BACKEND_URL}/api/track/pageview`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, referrer }),
      keepalive: true as any,
    }).catch(() => {});
  } catch {}
}
