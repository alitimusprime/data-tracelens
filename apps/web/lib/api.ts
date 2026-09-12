"use client";

import { useCallback, useEffect, useState } from "react";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
    cache: "no-store",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(body.detail || `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function useLiveQuery<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setData(await api<T>(path));
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "TraceLens API is unavailable");
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    const initial = window.setTimeout(() => void refresh(), 0);
    const events = new EventSource(`${API_URL}/api/events`);
    events.onmessage = () => void refresh();
    const fallback = window.setInterval(refresh, 15000);
    return () => {
      events.close();
      window.clearTimeout(initial);
      window.clearInterval(fallback);
    };
  }, [refresh]);

  return { data, error, loading, refresh };
}
