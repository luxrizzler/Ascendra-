import { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Flame, X } from "lucide-react";

const MESSAGES = {
  3: { title: "3-day streak!", body: "You're building the habit. Don't break the chain." },
  7: { title: "One full week!", body: "Most people quit by now. Not you." },
  14: { title: "Two weeks strong.", body: "You've outlasted 87% of new learners. Real momentum." },
  30: { title: "A whole month!", body: "This is what mastery looks like. Permanent neural rewiring in progress." },
  60: { title: "60 days.", body: "You're now in the top 1% of consistency on Ascendra." },
  100: { title: "Triple digits.", body: "You're a legend. Send us your story — we want to feature you." },
  365: { title: "365 days.", body: "A full year of showing up. We bow." },
};

export function StreakMilestoneModal({ open, days, onClose }) {
  useEffect(() => {
    if (!open) return;
    const t = setTimeout(onClose, 9000);
    return () => clearTimeout(t);
  }, [open, onClose]);
  const meta = MESSAGES[days] || { title: `${days}-day streak!`, body: "Keep going." };
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          className="fixed inset-0 z-[300] grid place-items-center p-4"
          style={{ background: "rgba(10,4,19,0.7)", backdropFilter: "blur(8px)" }}
          onClick={onClose}
          data-testid="milestone-modal"
        >
          <motion.div
            initial={{ scale: 0.85, y: 30, opacity: 0 }}
            animate={{ scale: 1, y: 0, opacity: 1 }}
            exit={{ scale: 0.95, y: 12, opacity: 0 }}
            transition={{ type: "spring", stiffness: 220, damping: 18 }}
            className="asc-card p-10 max-w-md w-full text-center relative overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <button onClick={onClose} className="absolute top-3 right-3 p-1.5 rounded-full hover:bg-white/5" data-testid="milestone-close-btn"><X size={16} /></button>
            <motion.div
              initial={{ scale: 0 }} animate={{ scale: [0, 1.3, 1] }} transition={{ duration: 0.6 }}
              className="w-24 h-24 rounded-full mx-auto grid place-items-center mb-4"
              style={{ background: "radial-gradient(circle at center, rgba(255,107,53,0.45), rgba(255,107,53,0.08))" }}
            >
              <Flame size={56} color="#FF6B35" fill="#FF6B35" />
            </motion.div>
            <div className="text-xs tracking-widest text-[#FFB000] font-black mb-1">MILESTONE</div>
            <h2 className="asc-h2 text-3xl">{meta.title}</h2>
            <p className="text-[var(--asc-text-dim)] mt-3 leading-relaxed">{meta.body}</p>
            <button onClick={onClose} className="asc-btn-primary mt-6 w-full justify-center" data-testid="milestone-continue-btn">Keep going 🔥</button>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
