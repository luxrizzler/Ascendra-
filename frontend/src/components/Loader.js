import { Sparkles } from "lucide-react";
export default function Loader({ label = "Loading…" }) {
  return (
    <div className="min-h-[40vh] grid place-items-center">
      <div className="flex flex-col items-center gap-3">
        <div className="animate-spin rounded-full" style={{ width: 28, height: 28, border: "3px solid rgba(255,176,0,0.25)", borderTopColor: "#FFB000" }} />
        <div className="text-[var(--asc-text-muted)] text-xs tracking-[0.25em] uppercase flex items-center gap-2"><Sparkles size={12} /> {label}</div>
      </div>
    </div>
  );
}
