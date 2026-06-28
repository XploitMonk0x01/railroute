"use client";

// ============================================================
// RailRoute AI — Search Store (Zustand)
// ============================================================

import { create } from "zustand";
import type {
  SearchResponse,
  FilterPreset,
  RouteResult,
} from "@/lib/types";

interface SearchState {
  // Query
  source: string;
  sourceName: string;
  destination: string;
  destinationName: string;
  date: string;
  travelClass: string;

  // Results
  results: SearchResponse | null;
  isLoading: boolean;
  error: string | null;

  // Filters
  filterPreset: FilterPreset;
  maxBudget: number | null;
  maxTransfers: number | null;

  // Actions
  setSource: (code: string, name: string) => void;
  setDestination: (code: string, name: string) => void;
  setDate: (date: string) => void;
  setTravelClass: (cls: string) => void;
  setResults: (results: SearchResponse) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setFilterPreset: (preset: FilterPreset) => void;
  setMaxBudget: (budget: number | null) => void;
  setMaxTransfers: (transfers: number | null) => void;
  swapStations: () => void;
  reset: () => void;

  // Computed
  getFilteredRoutes: () => RouteResult[];
}

// Sort weights for each preset
const PRESET_SORT: Record<FilterPreset, (a: RouteResult, b: RouteResult) => number> = {
  default: (a, b) => a.score - b.score,
  fastest: (a, b) => a.total_time_min - b.total_time_min,
  cheapest: (a, b) => a.total_fare - b.total_fare,
  least_transfers: (a, b) => a.transfer_count - b.transfer_count || a.total_time_min - b.total_time_min,
  best_availability: (a, b) => a.score - b.score, // availability-weighted score from backend
};

export const useSearchStore = create<SearchState>((set, get) => ({
  source: "",
  sourceName: "",
  destination: "",
  destinationName: "",
  date: "",
  travelClass: "3A",

  results: null,
  isLoading: false,
  error: null,

  filterPreset: "default",
  maxBudget: null,
  maxTransfers: null,

  setSource: (code, name) => set({ source: code, sourceName: name }),
  setDestination: (code, name) => set({ destination: code, destinationName: name }),
  setDate: (date) => set({ date }),
  setTravelClass: (cls) => set({ travelClass: cls }),
  setResults: (results) => set({ results, isLoading: false, error: null }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error, isLoading: false }),
  setFilterPreset: (filterPreset) => set({ filterPreset }),
  setMaxBudget: (maxBudget) => set({ maxBudget }),
  setMaxTransfers: (maxTransfers) => set({ maxTransfers }),
  swapStations: () =>
    set((state) => ({
      source: state.destination,
      sourceName: state.destinationName,
      destination: state.source,
      destinationName: state.sourceName,
    })),
  reset: () =>
    set({
      source: "",
      sourceName: "",
      destination: "",
      destinationName: "",
      date: "",
      travelClass: "3A",
      results: null,
      isLoading: false,
      error: null,
      filterPreset: "default",
      maxBudget: null,
      maxTransfers: null,
    }),

  getFilteredRoutes: () => {
    const { results, filterPreset, maxBudget, maxTransfers } = get();
    if (!results) return [];

    let routes = [...results.alternatives];

    if (maxBudget !== null) {
      routes = routes.filter((r) => r.total_fare <= maxBudget);
    }
    if (maxTransfers !== null) {
      routes = routes.filter((r) => r.transfer_count <= maxTransfers);
    }

    routes.sort(PRESET_SORT[filterPreset]);
    return routes;
  },
}));
