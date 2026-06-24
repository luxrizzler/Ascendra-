// shadcn cn helper
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
export function cn(...inputs) { return twMerge(clsx(inputs)); }

export function tierRank(t) {
  return { free: 0, ascender: 1, pathfinder: 2, sage: 3 }[t] ?? 0;
}
export function canAccess(userTier, pathTier) {
  return tierRank(userTier) >= tierRank(pathTier);
}

export function formatDate(iso) {
  if (!iso) return "";
  try { return new Date(iso).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" }); } catch { return ""; }
}
