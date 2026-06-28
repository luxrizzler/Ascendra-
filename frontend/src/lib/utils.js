// shadcn cn helper
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
export function cn(...inputs) { return twMerge(clsx(inputs)); }

export function tierRank(t) {
  return { free: 0, ascender: 1, pathfinder: 2, sage: 3 }[t] ?? 0;
}
/**
 * Returns true if the user can access content at the given tier.
 *
 * Accepts either a tier string (legacy) or a user object. When given a user
 * object, admins (is_admin: true) always pass — they need to QA every path
 * regardless of which paid tier the content is locked to.
 */
export function canAccess(userOrTier, pathTier) {
  if (userOrTier && typeof userOrTier === "object") {
    if (userOrTier.is_admin) return true;
    return tierRank(userOrTier.tier) >= tierRank(pathTier);
  }
  return tierRank(userOrTier) >= tierRank(pathTier);
}

export function formatDate(iso) {
  if (!iso) return "";
  try { return new Date(iso).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" }); } catch { return ""; }
}
