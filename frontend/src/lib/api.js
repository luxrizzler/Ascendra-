// Ascendra API client. Adds Bearer token from localStorage automatically.
import axios from "axios";

const BACKEND = process.env.REACT_APP_BACKEND_URL;
export const TOKEN_KEY = "ascendra_token";

export const apiBase = `${BACKEND}/api`;

export function getToken() {
  try { return localStorage.getItem(TOKEN_KEY) || ""; } catch { return ""; }
}
export function setToken(t) {
  try {
    if (t) localStorage.setItem(TOKEN_KEY, t);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {}
}

const client = axios.create({ baseURL: apiBase, timeout: 60000 });
client.interceptors.request.use((cfg) => {
  const t = getToken();
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

function prettyError(e) {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return new Error(d);
  if (Array.isArray(d) && d[0]?.msg) return new Error(d[0].msg);
  if (e?.message) return new Error(e.message);
  return new Error("Request failed");
}

export const api = {
  get:   async (p)       => { try { const r = await client.get(p);       return r.data; } catch (e) { throw prettyError(e); } },
  post:  async (p, body) => { try { const r = await client.post(p, body); return r.data; } catch (e) { throw prettyError(e); } },
  put:   async (p, body) => { try { const r = await client.put(p, body);  return r.data; } catch (e) { throw prettyError(e); } },
  patch: async (p, body) => { try { const r = await client.patch(p, body);return r.data; } catch (e) { throw prettyError(e); } },
  del:   async (p)       => { try { const r = await client.delete(p);    return r.data; } catch (e) { throw prettyError(e); } },
};

export const BACKEND_URL = BACKEND;
