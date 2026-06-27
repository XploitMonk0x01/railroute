// ============================================================
// RailRoute AI — Shared formatting utilities
// ============================================================

/** Format HH:MM:SS or HH:MM backend time to HH:MM display */
export function formatTime(timeStr: string): string {
  if (!timeStr) return "--:--";
  const parts = timeStr.split(":");
  return `${parts[0].padStart(2, "0")}:${parts[1].padStart(2, "0")}`;
}

/** Format duration in minutes to Xh Ym */
export function formatDuration(minutes: number): string {
  if (!minutes || minutes <= 0) return "0m";
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m}m`;
  if (m === 0) return `${h}h`;
  return `${h}h ${m}m`;
}

/** Format fare in Indian Rupees */
export function formatFare(fare: number): string {
  if (fare === undefined || fare === null) return "₹0";
  return `₹${Math.round(fare).toLocaleString("en-IN")}`;
}
