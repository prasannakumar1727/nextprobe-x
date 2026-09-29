import { useEffect, useState } from "react";
export async function api<T = any>(path: string, opts?: RequestInit): Promise<T> {
  const r = await fetch("/api" + path, opts);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.detail || `HTTP ${r.status}`);
  return body as T;
}
export const post = <T = any>(p: string, b?: unknown) => api<T>(p, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(b ?? {}) });
export function useApi<T = any>(path: string | null, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null); const [error, setError] = useState<string | null>(null); const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!path) return; let live = true; setLoading(true); setError(null);
    api<T>(path).then(d => live && setData(d)).catch(e => live && setError(String(e.message))).finally(() => live && setLoading(false));
    return () => { live = false; };
  }, [path, ...deps]);
  return { data, error, loading };
}
