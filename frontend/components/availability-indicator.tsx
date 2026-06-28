"use client";

interface AvailabilityIndicatorProps {
  availability: string;
  className?: string;
}

export function AvailabilityIndicator({ availability, className }: AvailabilityIndicatorProps) {
  const upper = availability.toUpperCase();

  let dotClass = "bg-emerald-500";
  let textClass = "text-emerald-700";
  let bgClass = "bg-emerald-50 border-emerald-200";
  let pulse = false;

  if (upper.startsWith("WL")) {
    dotClass = "bg-orange-500";
    textClass = "text-orange-700";
    bgClass = "bg-orange-50 border-orange-200";
    pulse = true;
  } else if (upper.startsWith("RAC")) {
    dotClass = "bg-amber-500";
    textClass = "text-amber-700";
    bgClass = "bg-amber-50 border-amber-200";
    pulse = true;
  } else if (upper.startsWith("REGRET")) {
    dotClass = "bg-red-500";
    textClass = "text-red-700";
    bgClass = "bg-red-50 border-red-200";
    pulse = false;
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${bgClass} ${textClass} ${className || ""}`}
    >
      <span className={`size-1.5 rounded-full ${dotClass} ${pulse ? "animate-pulse" : ""}`} />
      {availability}
    </span>
  );
}
