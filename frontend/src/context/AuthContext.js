import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, getToken, setToken } from "@/lib/api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!getToken()) { setUser(null); setLoading(false); return null; }
    try {
      const u = await api.get("/auth/me");
      setUser(u);
      return u;
    } catch {
      setToken("");
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const login = async (email, password) => {
    const { access_token } = await api.post("/auth/login", { email, password });
    setToken(access_token);
    return await refresh();
  };

  const signup = async (email, password, name) => {
    const { access_token } = await api.post("/auth/signup", { email, password, name });
    setToken(access_token);
    return await refresh();
  };

  const logout = () => {
    setToken("");
    setUser(null);
  };

  return (
    <AuthCtx.Provider value={{ user, loading, login, signup, logout, refresh, setUser }}>
      {children}
    </AuthCtx.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}
