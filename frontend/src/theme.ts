// Ascendra design system — Celestial Phoenix palette.
// Mirrors the brand guide: deep navy + golden dawn + celestial violet.
export const C = {
  // Backgrounds
  bg: "#070B1F",            // Deep Navy
  surface: "#141A38",       // Slightly elevated card
  surface2: "#1F2649",      // Higher elevation / inputs
  celestial: "#1A1F3D",     // Mid surface (per palette)

  // Text
  text: "#FFFFFF",
  textDim: "#C8C5E6",       // Soft lavender-tinted body text
  textMuted: "#7E84A3",

  // Brand accents
  brand: "#FFB000",         // Amber Gold (primary CTA)
  brandSoft: "#E8C572",     // Champagne (soft gold)
  brandDim: "rgba(255, 176, 0, 0.15)",
  coral: "#FF6B35",         // Phoenix Coral (accent / fire)
  lavender: "#BFB4FF",      // Lavender Mist
  violet: "#7C3AED",        // Celestial Violet (secondary)
  violetDim: "rgba(124, 58, 237, 0.18)",

  // Semantic
  success: "#34D399",
  danger: "#F87171",
  info: "#BFB4FF",

  // Borders
  border: "rgba(191, 180, 255, 0.12)",
  borderStrong: "rgba(191, 180, 255, 0.28)",
};

// Gradient stops (use with expo-linear-gradient `colors` prop)
export const GRAD = {
  goldenDawn: ["#E8C572", "#FFB000", "#FF6B35"] as const,
  celestialViolet: ["#1A1F3D", "#7C3AED", "#BFB4FF"] as const,
  heroOverlay: ["rgba(7,11,31,0.0)", "rgba(7,11,31,0.65)", "rgba(7,11,31,0.98)"] as const,
  cardGlow: ["rgba(124,58,237,0.18)", "transparent"] as const,
};

export const RADIUS = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  pill: 999,
};
