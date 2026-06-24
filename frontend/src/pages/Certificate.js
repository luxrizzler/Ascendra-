import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { api } from "@/lib/api";
import Loader from "@/components/Loader";
import { formatDate } from "@/lib/utils";
import { ArrowLeft, Printer, Sparkles, Share2 } from "lucide-react";
import { toast } from "sonner";

export default function Certificate() {
  const { certId } = useParams();
  const nav = useNavigate();
  const [cert, setCert] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get(`/certificates/${certId}`)
      .then(setCert)
      .catch(() => toast.error("Could not load certificate"))
      .finally(() => setLoading(false));
  }, [certId]);

  if (loading) return <Loader />;
  if (!cert) return null;

  const share = async () => {
    const url = `${window.location.origin}/certificate/${certId}`;
    if (navigator.share) {
      try { await navigator.share({ title: `Ascendra Certificate · ${cert.path_title}`, url }); } catch {}
    } else {
      try { await navigator.clipboard.writeText(url); toast.success("Link copied!"); } catch {}
    }
  };

  return (
    <div className="min-h-screen px-5 py-8" data-testid="certificate-page" style={{ background: "#0A0413" }}>
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-6 no-print">
          <button onClick={() => nav(-1)} className="flex items-center gap-2 text-sm text-[var(--asc-text-dim)] hover:text-white" data-testid="cert-back-btn"><ArrowLeft size={16} /> Back</button>
          <div className="flex gap-2">
            <button onClick={share} className="asc-btn-secondary text-sm" data-testid="cert-share-btn"><Share2 size={14} /> Share</button>
            <button onClick={() => window.print()} className="asc-btn-primary text-sm" data-testid="cert-print-btn"><Printer size={14} /> Print / Save PDF</button>
          </div>
        </div>

        {/* CERT */}
        <div className="relative rounded-3xl overflow-hidden print-cert" style={{ background: "linear-gradient(135deg, #15102B, #0A0413)", border: `2px solid ${cert.path_color}` }}>
          {/* Decorative corner */}
          <div className="absolute -top-20 -right-20 w-60 h-60 rounded-full slow-spin" style={{ background: `radial-gradient(circle, ${cert.path_color}33, transparent 70%)` }} />
          <div className="absolute -bottom-20 -left-20 w-60 h-60 rounded-full slow-spin" style={{ background: "radial-gradient(circle, rgba(124,58,237,0.25), transparent 70%)", animationDirection: "reverse" }} />

          <div className="relative p-10 sm:p-16 text-center">
            <div className="flex items-center justify-center gap-2">
              <div className="w-9 h-9 rounded-lg grid place-items-center" style={{ background: "#FFB000" }}><Sparkles size={18} color="#000" /></div>
              <span className="font-black tracking-[0.4em] text-base text-white">ASCENDRA</span>
            </div>
            <div className="w-16 h-0.5 mx-auto mt-3" style={{ background: cert.path_color }} />
            <div className="asc-kicker mt-8" style={{ color: cert.path_color }}>Certificate of Completion</div>
            <p className="text-[var(--asc-text-dim)] mt-6 text-sm uppercase tracking-[0.25em]">This certifies that</p>
            <h1 className="text-3xl sm:text-5xl font-black mt-3 italic" style={{ color: cert.path_color, letterSpacing: "-0.02em" }}>{cert.user_name}</h1>
            <p className="text-[var(--asc-text-dim)] mt-6 text-sm uppercase tracking-[0.25em]">Has completed the path</p>
            <h2 className="asc-h2 text-2xl sm:text-3xl mt-3 text-white">{cert.path_title}</h2>
            <p className="text-[var(--asc-text-dim)] mt-8 max-w-md mx-auto">In recognition of mastery, dedication, and the courage to rise.</p>

            <div className="flex items-center justify-center gap-10 sm:gap-16 mt-12 flex-wrap">
              <div>
                <div className="text-[10px] uppercase tracking-[0.25em] text-[var(--asc-text-muted)]">Issued</div>
                <div className="font-bold mt-1" style={{ color: cert.path_color }}>{formatDate(cert.issued_at)}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.25em] text-[var(--asc-text-muted)]">Serial</div>
                <div className="font-bold mt-1 asc-mono" style={{ color: cert.path_color }}>{cert.serial}</div>
              </div>
            </div>
          </div>
        </div>

        <div className="text-center mt-6 text-xs text-[var(--asc-text-muted)] no-print">
          Verify this certificate by visiting <Link to={`/certificate/${cert.id}`} className="text-[var(--asc-brand)]">/certificate/{cert.id.slice(0, 8)}</Link>
        </div>
      </div>
    </div>
  );
}
