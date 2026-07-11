import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "@/lib/api";
import { toast } from "sonner";
import SEO from "@/components/SEO";
import Loader from "@/components/Loader";
import {
  Trophy, Award, Medal, Flame, Target, Sparkles, Share2, GraduationCap,
  Lock, Star, ArrowRight,
} from "lucide-react";

/**
 * Trophy Case — shareable award showcase.
 * Renders in two modes:
 *   - Private (route: /trophy-case) — the current user's own awards
 *   - Public  (route: /trophy-case/:userSlug) — anyone can view
 */
export default function TrophyCase({ isPublic = false }) {
  const { userSlug } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);

  useEffect(() => {
    const url = isPublic
      ? `/trophy-case/public/${encodeURIComponent(userSlug)}`
      : "/trophy-case/mine";
    api.get(url)
      .then(setData)
      .catch((e) => setErr(e.message || "Not found"))
      .finally(() => setLoading(false));
  }, [isPublic, userSlug]);

  const copyLink = () => {
    if (!data?.user) return;
    const email = data.user.name && data.user.name.includes("@") ? data.user.name : null;
    // If we have an email/id — prefer the public form. Otherwise, share the current URL.
    const url = `${window.location.origin}/trophy-case/${encodeURIComponent(userSlug || "")}`;
    navigator.clipboard?.writeText(url.replace("/undefined", "").replace("/trophy-case/", "/trophy-case/"));
    toast.success("Trophy case link copied!");
  };

  if (loading) return <div className="min-h-screen grid place-items-center"><Loader /></div>;
  if (err) return (
    <div className="min-h-screen grid place-items-center px-6">
      <div className="asc-card p-10 text-center max-w-md">
        <Trophy size={28} color="#BFB4FF" className="mx-auto" />
        <h1 className="asc-h2 text-2xl mt-4">Trophy case not found</h1>
        <p className="text-[var(--asc-text-dim)] mt-2">{err}</p>
        <Link to="/" className="asc-btn-primary mt-6 inline-flex">Return home</Link>
      </div>
    </div>
  );

  const { user, stats, certificates, capstone_badges, streak_trophies, mastery_medals } = data;
  const displayName = user.name || "Ascendra learner";

  return (
    <div className="min-h-screen" data-testid="trophy-case-page">
      <SEO
        title={`${displayName}'s Trophy Case — Ascendra Academy`}
        description={`${displayName} has earned ${stats.total_earned} awards on Ascendra Academy: ${stats.certificates} certificates, ${stats.capstones} capstones, ${stats.practices_mastered} mastered practices.`}
        path={isPublic ? `/trophy-case/${userSlug}` : "/trophy-case"}
        noindex={!isPublic}
      />

      {/* Hero */}
      <section className="px-6 pt-14 pb-10 border-b border-[var(--asc-border)]">
        <div className="max-w-6xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border mb-5" style={{ background: "linear-gradient(90deg, rgba(255,176,0,0.15), rgba(255,107,53,0.10))", borderColor: "rgba(255,176,0,0.4)" }}>
            <Trophy size={13} color="#FFB000" />
            <span className="asc-label" style={{ color: "#FFB000" }}>Trophy Case</span>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-6">
            <div className="flex items-center gap-5">
              {user.picture ? (
                <img src={user.picture} alt={displayName} className="w-20 h-20 rounded-full border-2 border-[#FFB000] shadow-2xl" />
              ) : (
                <div className="w-20 h-20 rounded-full grid place-items-center border-2 border-[#FFB000] shadow-2xl" style={{ background: "linear-gradient(135deg, rgba(255,176,0,0.25), rgba(255,107,53,0.15))" }}>
                  <span className="text-3xl font-black text-white">{displayName[0]?.toUpperCase()}</span>
                </div>
              )}
              <div>
                <h1 className="asc-h1 text-4xl sm:text-5xl" data-testid="trophy-case-name">{displayName}</h1>
                <p className="text-[var(--asc-text-dim)] mt-1">
                  <span className="font-black text-white text-lg">{stats.total_earned}</span> award{stats.total_earned === 1 ? "" : "s"} earned on Ascendra Academy
                </p>
              </div>
            </div>
            {!isPublic && (
              <button onClick={copyLink} className="asc-btn-primary" data-testid="trophy-case-share-btn">
                <Share2 size={14} /> Share trophy case
              </button>
            )}
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="px-6 pt-6">
        <div className="max-w-6xl mx-auto grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatBox icon={GraduationCap} label="Certificates" value={stats.certificates} color="#FFB000" />
          <StatBox icon={Award} label="Capstones" value={stats.capstones} color="#22c55e" />
          <StatBox icon={Target} label="Mastered" value={stats.practices_mastered} color="#BFB4FF" />
          <StatBox icon={Flame} label="Longest streak" value={`${stats.longest_streak}d`} color="#FF6B35" />
        </div>
      </section>

      {/* Certificates */}
      <TrophySection title="Certificates" subtitle="Full learning paths completed" icon={GraduationCap}>
        {certificates.length === 0 ? (
          <EmptyCase text="No certificates earned yet. Complete a full learning path to unlock." cta={!isPublic ? { to: "/paths", label: "Browse paths" } : null} />
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {certificates.map((c) => (
              <CertCard key={c.id} cert={c} />
            ))}
          </div>
        )}
      </TrophySection>

      {/* Capstone Badges */}
      <TrophySection title="Capstone Badges" subtitle="Applied projects passed with AI grading" icon={Award}>
        {capstone_badges.length === 0 ? (
          <EmptyCase text="No capstones passed yet. Pass a module capstone to earn your first badge." />
        ) : (
          <div className="grid sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {capstone_badges.map((b) => (
              <BadgeCard key={b.attempt_id} badge={b} />
            ))}
          </div>
        )}
      </TrophySection>

      {/* Streak Trophies */}
      <TrophySection title="Streak Trophies" subtitle="Consistency awards" icon={Flame}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {streak_trophies.map((t) => (
            <TrophyTile key={t.days} label={t.name} sublabel={`${t.days}-day streak`} earned={t.earned} icon={Flame} color="#FF6B35" testid={`streak-${t.days}`} />
          ))}
        </div>
      </TrophySection>

      {/* Mastery Medals */}
      <TrophySection title="Mastery Medals" subtitle="Practice challenges mastered" icon={Medal}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {mastery_medals.map((m) => (
            <TrophyTile key={m.count} label={m.name} sublabel={`${m.count} mastered`} earned={m.earned} icon={Medal} color="#BFB4FF" testid={`mastery-${m.count}`} />
          ))}
        </div>
      </TrophySection>

      {/* Public CTA */}
      {isPublic && (
        <section className="px-6 pb-16">
          <div className="max-w-3xl mx-auto p-6 rounded-2xl text-center" style={{ background: "linear-gradient(135deg, rgba(255,176,0,0.08), rgba(191,180,255,0.08))", border: "1px solid var(--asc-border)" }}>
            <Sparkles size={20} color="#FFB000" className="mx-auto" />
            <h3 className="asc-h2 text-xl mt-3">Start earning your own trophies</h3>
            <p className="text-[var(--asc-text-dim)] mt-2 text-sm">Learn AI through interactive lessons, applied practice, and real-project capstones. Free to start.</p>
            <Link to="/signup" className="asc-btn-primary mt-4 inline-flex" data-testid="trophy-case-public-cta">
              Create your free account <ArrowRight size={14} />
            </Link>
          </div>
        </section>
      )}
    </div>
  );
}

function StatBox({ icon: Icon, label, value, color }) {
  return (
    <div className="asc-card p-4">
      <div className="flex items-center gap-1.5 mb-1">
        <Icon size={13} color={color} />
        <span className="asc-label" style={{ color, fontSize: 10 }}>{label}</span>
      </div>
      <div className="text-3xl font-black text-white">{value}</div>
    </div>
  );
}

function TrophySection({ title, subtitle, icon: Icon, children }) {
  return (
    <section className="px-6 py-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-baseline gap-3 mb-5">
          <Icon size={18} color="#FFB000" />
          <h2 className="asc-h2 text-2xl">{title}</h2>
          <span className="text-xs text-[var(--asc-text-muted)]">{subtitle}</span>
        </div>
        {children}
      </div>
    </section>
  );
}

function CertCard({ cert }) {
  const color = cert.path_color || "#FFB000";
  return (
    <div className="asc-card p-5 relative overflow-hidden" data-testid={`cert-${cert.id}`}>
      <div className="absolute -top-8 -right-8 w-28 h-28 rounded-full opacity-20" style={{ background: color }} />
      <div className="relative">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-10 h-10 rounded-lg grid place-items-center" style={{ background: `${color}25`, border: `1px solid ${color}80` }}>
            <GraduationCap size={18} color={color} />
          </div>
          <div className="text-xs text-[var(--asc-text-muted)] tracking-wider">CERTIFICATE</div>
        </div>
        <h3 className="font-black text-white text-lg leading-tight">{cert.path_title}</h3>
        {cert.capstones_passed > 0 && (
          <div className="mt-1 text-xs" style={{ color: "#22c55e" }}>+ {cert.capstones_passed} capstone{cert.capstones_passed === 1 ? "" : "s"} passed</div>
        )}
        <div className="mt-3 text-xs text-[var(--asc-text-muted)] font-mono">{cert.serial}</div>
        <div className="text-xs text-[var(--asc-text-muted)] mt-1">
          Issued {cert.issued_at ? new Date(cert.issued_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : ""}
        </div>
      </div>
    </div>
  );
}

function BadgeCard({ badge }) {
  return (
    <div className="asc-card p-4 flex flex-col items-center text-center relative" data-testid={`badge-${badge.attempt_id}`}>
      <div className="w-14 h-14 rounded-full grid place-items-center mb-3" style={{ background: "linear-gradient(135deg, rgba(34,197,94,0.25), rgba(255,176,0,0.15))", border: "1px solid rgba(34,197,94,0.5)" }}>
        <Award size={22} color="#22c55e" />
      </div>
      <div className="font-bold text-white text-sm leading-tight line-clamp-2">{badge.title}</div>
      <div className="mt-2 flex items-center gap-1 text-xs" style={{ color: "#22c55e" }}>
        <Star size={11} fill="#22c55e" /> {badge.score}
      </div>
      <div className="text-[10px] text-[var(--asc-text-muted)] mt-1">
        {badge.earned_at ? new Date(badge.earned_at).toLocaleDateString(undefined, { month: "short", day: "numeric" }) : ""}
      </div>
    </div>
  );
}

function TrophyTile({ label, sublabel, earned, icon: Icon, color, testid }) {
  return (
    <div className="asc-card p-4 flex flex-col items-center text-center relative transition" style={{ opacity: earned ? 1 : 0.4, borderColor: earned ? `${color}80` : "var(--asc-border)" }} data-testid={testid}>
      {!earned && (
        <div className="absolute top-2 right-2">
          <Lock size={11} color="#94a3b8" />
        </div>
      )}
      <div className="w-16 h-16 rounded-full grid place-items-center mb-3" style={{ background: earned ? `linear-gradient(135deg, ${color}30, ${color}12)` : "rgba(148,163,184,0.08)", border: `2px solid ${earned ? color : "rgba(148,163,184,0.25)"}` }}>
        <Icon size={26} color={earned ? color : "#94a3b8"} />
      </div>
      <div className="font-bold text-sm text-white leading-tight">{label}</div>
      <div className="text-xs text-[var(--asc-text-muted)] mt-1">{sublabel}</div>
      {earned && <div className="text-[10px] mt-2 font-black tracking-wider" style={{ color }}>EARNED</div>}
    </div>
  );
}

function EmptyCase({ text, cta }) {
  return (
    <div className="asc-card p-8 text-center">
      <p className="text-[var(--asc-text-dim)] text-sm">{text}</p>
      {cta && (
        <Link to={cta.to} className="asc-btn-secondary mt-4 inline-flex text-sm">
          {cta.label} <ArrowRight size={13} />
        </Link>
      )}
    </div>
  );
}
