import { Sparkles } from "lucide-react";
import { Link } from "react-router-dom";

export default function WebFooter() {
  return (
    <footer className="border-t border-[var(--asc-border)] mt-20">
      <div className="max-w-7xl mx-auto px-6 py-12 grid md:grid-cols-4 gap-10">
        <div className="md:col-span-2">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: "#FFB000" }}>
              <Sparkles size={15} color="#000" />
            </div>
            <span className="font-black tracking-[0.32em] text-sm">ASCENDRA</span>
          </div>
          <p className="text-[var(--asc-text-dim)] text-sm mt-3 max-w-md">
            The AI learning partner that walks beside you — from your first prompt to your first launch.
          </p>
        </div>
        <div>
          <div className="asc-label mb-3">Product</div>
          <ul className="space-y-2 text-sm text-[var(--asc-text-dim)]">
            <li><Link to="/paths" className="hover:text-white">Learning Paths</Link></li>
            <li><Link to="/models" className="hover:text-white">AI Models</Link></li>
            <li><Link to="/tutor" className="hover:text-white">AI Tutor</Link></li>
            <li><Link to="/pricing" className="hover:text-white">Pricing</Link></li>
          </ul>
        </div>
        <div>
          <div className="asc-label mb-3">Account</div>
          <ul className="space-y-2 text-sm text-[var(--asc-text-dim)]">
            <li><Link to="/login" className="hover:text-white">Sign in</Link></li>
            <li><Link to="/signup" className="hover:text-white">Create account</Link></li>
            <li><Link to="/forgot-password" className="hover:text-white">Forgot password</Link></li>
          </ul>
        </div>
      </div>
      <div className="max-w-7xl mx-auto px-6 pb-10 text-[var(--asc-text-muted)] text-xs flex flex-wrap items-center justify-between gap-3">
        <span>© 2026 Ascendra Academy · Learn. Grow. Transform. Ascend.</span>
        <span>Powered by GPT-5.2 · Claude 4.5 · Gemini 3</span>
      </div>
    </footer>
  );
}
