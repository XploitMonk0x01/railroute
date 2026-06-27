// ============================================================
// RailRoute AI — TypeScript Types
// Mirrors the API response shapes defined in the architecture
// ============================================================

// ---- Station ----
export interface Station {
  code: string;
  name: string;
  city: string;
  state: string;
  score: number;
  is_junction: boolean;
}

// ---- Train ----
export interface Train {
  id: number;
  train_number: string;
  train_name: string;
  train_type: TrainType;
  origin_code: string;
  destination_code: string;
  total_distance: number;
  run_days: string; // bitmask string "1111100"
  is_active: boolean;
}

export type TrainType =
  | "Rajdhani"
  | "Shatabdi"
  | "Duronto"
  | "SF Express"
  | "Express"
  | "Superfast"
  | "Passenger"
  | "Garib Rath"
  | "Humsafar"
  | "Tejas"
  | "Vande Bharat";

// ---- Route Segment (one leg of a journey) ----
export interface RouteSegment {
  train_number: string;
  train_name: string;
  train_type: string;
  from: string;        // station code
  from_name: string;
  to: string;          // station code
  to_name: string;
  departure: string;   // "HH:MM:SS"
  arrival: string;     // "HH:MM:SS"
  duration_min: number;
  distance_km: number;
  class: string;
  fare: number;
  availability: string; // "AVAILABLE (12)", "WL"
  is_transfer: boolean;
  wait_min: number;
  day: number;
}

// ---- Route Result (a complete alternative route) ----
export interface RouteResult {
  route_id: string;
  score: number;
  total_time_min: number;
  total_fare: number;
  transfer_count: number;
  total_wait_min: number;  // aliased from wait_min in backend
  segments: RouteSegment[];
}

// ---- Search Response ----
export interface SearchResponse {
  direct_available: boolean;
  direct_train: RouteSegment | null;
  alternatives: RouteResult[];
  generated_at: string; // ISO timestamp
}

// ---- Search Request ----
export interface SearchRequest {
  source: string;
  destination: string;
  date: string; // YYYY-MM-DD
  class?: string;
  constraints?: SearchConstraints;
}

export interface SearchConstraints {
  max_transfers?: number;
  max_wait_min?: number;
  max_budget?: number;
}

// ---- Availability ----
export type AvailabilityStatus = "AVAILABLE" | "WL" | "REGRET" | "RAC";

export interface SeatAvailability {
  train_number: string;
  journey_date: string;
  class_code: string;
  from_station: string;
  to_station: string;
  available_seats: number;
  wl_number: number;
  status: AvailabilityStatus;
  quota: string;
  fare: number;
}

// ---- Watchlist ----
export interface WatchlistEntry {
  id: number;
  source_code: string;
  source_name: string;
  destination_code: string;
  destination_name: string;
  journey_date: string;
  preferred_class: string;
  max_budget: number;
  notify_on: string[];
  is_active: boolean;
  created_at: string;
  latest_status?: string;
}

// ---- Filter Preset ----
export type FilterPreset =
  | "default"
  | "fastest"
  | "cheapest"
  | "least_transfers"
  | "best_availability";

// ---- User ----
export interface User {
  id: number;
  email: string;
  display_name: string;
  phone?: string;
}
