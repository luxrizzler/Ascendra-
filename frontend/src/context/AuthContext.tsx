import React, { createContext, useContext, useEffect, useState, ReactNode, useCallback } from "react";
import { storage } from "@/src/utils/storage";
import { api, TOKEN_KEY } from "@/src/api";

export type User = {
  id: string;
  email: string;
  name?: string;
  goal?: string;
  tier: "free" | "pro" | "business";
};

type AuthCtx = {
  user: User | null;
  loading: boolean;
  signup: (email: string, password: string, name?: string, goal?: string) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
};

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const me = await api.get("/auth/me");
      setUser(me);
    } catch {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    (async () => {
      const t = await storage.secureGet(TOKEN_KEY, "");
      if (t) await refresh();
      setLoading(false);
    })();
  }, [refresh]);

  const signup = async (email: string, password: string, name?: string, goal?: string) => {
    const { access_token } = await api.post("/auth/signup", { email, password, name, goal });
    await storage.secureSet(TOKEN_KEY, access_token);
    await refresh();
  };

  const login = async (email: string, password: string) => {
    const { access_token } = await api.post("/auth/login", { email, password });
    await storage.secureSet(TOKEN_KEY, access_token);
    await refresh();
  };

  const logout = async () => {
    await storage.secureRemove(TOKEN_KEY);
    setUser(null);
  };

  return (
    <Ctx.Provider value={{ user, loading, signup, login, logout, refresh }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAuth() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth must be used inside AuthProvider");
  return c;
}
