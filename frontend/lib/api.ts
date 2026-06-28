// ============================================================
// RailRoute AI — API Client
// Fully integrated with FastAPI Backend
// ============================================================

import type {
  SearchRequest,
  SearchResponse,
  Station,
  WatchlistEntry,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

// ---- Generic fetch wrapper ----
async function apiFetch<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API Error: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

// ---- Station autocomplete ----
export async function getStations(query: string): Promise<Station[]> {
  return apiFetch<Station[]>(`/stations?q=${encodeURIComponent(query)}`);
}

// ---- Route search ----
export async function searchRoutes(
  params: SearchRequest
): Promise<SearchResponse> {
  return apiFetch<SearchResponse>("/search", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

// ---- Watchlist ----
export async function getWatchlist(): Promise<WatchlistEntry[]> {
  return apiFetch<WatchlistEntry[]>("/watchlist");
}

export async function createWatchlistEntry(
  data: Omit<WatchlistEntry, "id" | "created_at" | "is_active" | "latest_status">
): Promise<WatchlistEntry> {
  return apiFetch<WatchlistEntry>("/watchlist", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteWatchlistEntry(id: number): Promise<void> {
  await apiFetch(`/watchlist/${id}`, { method: "DELETE" });
}
