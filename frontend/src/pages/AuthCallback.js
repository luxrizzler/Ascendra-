// Auth callback handler for Emergent-managed Google OAuth.
// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { api, setToken } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import Loader from "@/components/Loader";

export default function AuthCallback() {
  const nav = useNavigate();
  const { refresh } = useAuth();
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    const hash = window.location.hash || "";
    const m = hash.match(/session_id=([^&]+)/);
    if (!m) {
      nav("/login");
      return;
    }
    const sessionId = decodeURIComponent(m[1]);

    (async () => {
      try {
        const { access_token } = await api.post("/auth/google", { session_token: sessionId });
        setToken(access_token);
        const user = await refresh();
        window.history.replaceState({}, "", window.location.pathname);
        toast.success(`Welcome${user?.name ? `, ${user.name.split(" ")[0]}` : "!"}`);
        nav(user?.must_change_password ? "/profile?force_change=1" : "/dashboard");
      } catch (e) {
        toast.error(e.message || "Google sign-in failed");
        nav("/login");
      }
    })();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <Loader label="Signing you in…" />;
}
