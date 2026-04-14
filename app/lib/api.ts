import type {
  PredictionsResponse,
  RecordResponse,
  HistoryEntry,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "/api";

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `API error: ${res.status}`);
  }
  return res.json();
}

export async function fetchPredictions(mode: "regular" | "playoffs" = "regular"): Promise<PredictionsResponse> {
  const params = mode === "playoffs" ? "?mode=playoffs" : "";
  return fetchJSON<PredictionsResponse>(`${BASE_URL}/predictions${params}`);
}

export async function fetchRecord(days?: number): Promise<RecordResponse> {
  const params = days ? `?days=${days}` : "";
  const raw = await fetchJSON<{ record: RecordResponse; pending_dates: string[] }>(
    `${BASE_URL}/record${params}`
  );
  return { ...raw.record, pending_dates: raw.pending_dates };
}

export async function fetchHistory(
  limit?: number,
  date?: string
): Promise<{ history: HistoryEntry[] }> {
  const params = new URLSearchParams();
  if (limit) params.set("limit", String(limit));
  if (date) params.set("date", date);
  const qs = params.toString();
  return fetchJSON<{ history: HistoryEntry[] }>(
    `${BASE_URL}/history${qs ? `?${qs}` : ""}`
  );
}

export async function lockPredictions(
  predictions: unknown[]
): Promise<{ saved: number; message: string }> {
  return fetchJSON(`${BASE_URL}/lock`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ predictions }),
  });
}

export async function updateResults(
  date?: string
): Promise<{ updated: number; message: string }> {
  return fetchJSON(`${BASE_URL}/update_results`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ date }),
  });
}
