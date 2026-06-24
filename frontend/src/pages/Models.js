import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import Loader from "@/components/Loader";

const CATEGORIES = ["All", "Text", "Image", "Video", "Audio", "Coding", "Search"];

export default function Models() {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [cat, setCat] = useState("All");
  const [q, setQ] = useState("");

  useEffect(() => {
    api.get("/models").then((r) => setModels(r.models)).finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    return models.filter((m) => {
      if (cat !== "All" && m.category !== cat) return false;
      if (q && !`${m.name} ${m.provider} ${m.tagline}`.toLowerCase().includes(q.toLowerCase())) return false;
      return true;
    });
  }, [models, cat, q]);

  if (loading) return <Loader />;

  return (
    <div className="max-w-7xl mx-auto px-5 sm:px-8 py-10" data-testid="models-page">
      <div className="asc-kicker">Models library</div>
      <h1 className="asc-h2 text-4xl sm:text-5xl mt-2">22 models that matter in 2026.</h1>
      <p className="text-[var(--asc-text-dim)] mt-2 max-w-2xl">From reasoning giants to image wizards — know each model's superpower and pricing tier.</p>

      <div className="flex flex-wrap items-center gap-3 mt-6">
        <input className="asc-input flex-1 min-w-[200px] max-w-md" placeholder="Search models…" value={q} onChange={(e) => setQ(e.target.value)} data-testid="models-search" />
        <div className="flex flex-wrap gap-2">
          {CATEGORIES.map((c) => (
            <button key={c} onClick={() => setCat(c)} data-testid={`models-cat-${c.toLowerCase()}`} className={`px-3 py-1.5 rounded-full text-sm font-bold transition ${cat === c ? "" : "text-[var(--asc-text-dim)] hover:text-white"}`}
              style={cat === c ? { background: "#FFB000", color: "#000" } : { background: "#1F183A", border: "1px solid rgba(191,180,255,0.15)" }}>{c}</button>
          ))}
        </div>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-8">
        {filtered.map((m) => (
          <div key={m.id} className="asc-card p-5" data-testid={`model-card-${m.id}`}>
            <div className="flex items-start gap-3">
              <div className="w-11 h-11 rounded-xl grid place-items-center shrink-0" style={{ background: `${m.color}28`, border: `1px solid ${m.color}66` }}>
                <span className="text-xs font-black" style={{ color: m.color }}>{m.name[0]}</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="asc-h2 text-lg truncate">{m.name}</h3>
                  <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full font-black" style={{ background: priceColor(m.pricing_hint), color: "#000" }}>{m.pricing_hint}</span>
                </div>
                <div className="text-xs text-[var(--asc-text-muted)]">{m.provider} · {m.category}</div>
              </div>
            </div>
            <p className="text-[var(--asc-text-dim)] text-sm mt-3 leading-relaxed">{m.tagline}</p>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {(m.use_cases || []).slice(0, 3).map((u) => (
                <span key={u} className="text-[10px] px-2 py-0.5 rounded-full" style={{ background: "#1F183A", border: "1px solid rgba(191,180,255,0.1)" }}>{u}</span>
              ))}
            </div>
            <div className="mt-3 text-xs text-[var(--asc-text-dim)] flex items-start gap-1.5">
              <span className="font-bold text-[var(--asc-brand)]">Strengths:</span>
              <span>{m.strengths}</span>
            </div>
          </div>
        ))}
      </div>
      {filtered.length === 0 && <div className="text-center text-[var(--asc-text-muted)] mt-10">No models match.</div>}
    </div>
  );
}

function priceColor(hint) {
  return {
    Free: "#34D399",
    Low: "#BFB4FF",
    Mid: "#FFB000",
    Premium: "#FF6B35",
  }[hint] || "#7E84A3";
}
