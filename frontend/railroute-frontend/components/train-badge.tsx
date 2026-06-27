"use client";

import { Badge } from "@/components/ui/badge";
import type { TrainType } from "@/lib/types";

const TRAIN_TYPE_CONFIG: Record<
  TrainType,
  { label: string; className: string }
> = {
  Rajdhani: {
    label: "Rajdhani",
    className:
      "bg-amber-500/15 text-amber-400 border-amber-500/30 hover:bg-amber-500/25",
  },
  Shatabdi: {
    label: "Shatabdi",
    className:
      "bg-sky-500/15 text-sky-400 border-sky-500/30 hover:bg-sky-500/25",
  },
  Duronto: {
    label: "Duronto",
    className:
      "bg-purple-500/15 text-purple-400 border-purple-500/30 hover:bg-purple-500/25",
  },
  "SF Express": {
    label: "SF Express",
    className:
      "bg-emerald-500/15 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/25",
  },
  Express: {
    label: "Express",
    className:
      "bg-blue-500/15 text-blue-400 border-blue-500/30 hover:bg-blue-500/25",
  },
  Superfast: {
    label: "Superfast",
    className:
      "bg-teal-500/15 text-teal-400 border-teal-500/30 hover:bg-teal-500/25",
  },
  Passenger: {
    label: "Passenger",
    className:
      "bg-zinc-500/15 text-zinc-400 border-zinc-500/30 hover:bg-zinc-500/25",
  },
  "Garib Rath": {
    label: "Garib Rath",
    className:
      "bg-rose-500/15 text-rose-400 border-rose-500/30 hover:bg-rose-500/25",
  },
  Humsafar: {
    label: "Humsafar",
    className:
      "bg-indigo-500/15 text-indigo-400 border-indigo-500/30 hover:bg-indigo-500/25",
  },
  Tejas: {
    label: "Tejas",
    className:
      "bg-orange-500/15 text-orange-400 border-orange-500/30 hover:bg-orange-500/25",
  },
  "Vande Bharat": {
    label: "Vande Bharat",
    className:
      "bg-cyan-500/15 text-cyan-400 border-cyan-500/30 hover:bg-cyan-500/25",
  },
};

interface TrainBadgeProps {
  type: string;
  className?: string;
}

export function TrainBadge({ type, className }: TrainBadgeProps) {
  const config = TRAIN_TYPE_CONFIG[type as TrainType] ?? {
    label: type,
    className: "bg-indigo-500/15 text-indigo-400 border-indigo-500/30 hover:bg-indigo-500/25",
  };
  return (
    <Badge
      variant="outline"
      className={`text-[10px] font-semibold tracking-wide uppercase transition-colors ${config.className} ${className || ""}`}
    >
      {config.label}
    </Badge>
  );
}
