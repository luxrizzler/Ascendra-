export default function TierBadge({ tier, className = "" }) {
  const COLOR = { free: "#7E84A3", ascender: "#34D399", pathfinder: "#FFB000", sage: "#7C3AED" }[tier] || "#7E84A3";
  return (
    <span className={`px-2 py-0.5 rounded-full text-[10px] font-black tracking-[0.18em] uppercase ${className}`} style={{ background: COLOR, color: "#000" }}>
      {tier}
    </span>
  );
}
