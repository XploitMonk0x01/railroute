"use client";

import { useSearchStore } from "@/store/search-store";
import type { FilterPreset } from "@/lib/types";
import { Zap, IndianRupee, ArrowLeftRight, ShieldCheck, LayoutGrid } from "lucide-react";
import { cn } from "@/lib/utils";

const PRESETS: {
  key: FilterPreset;
  label: string;
  icon: typeof Zap;
}[] = [
  { key: "default", label: "Smart Sort", icon: LayoutGrid },
  { key: "fastest", label: "Fastest", icon: Zap },
  { key: "cheapest", label: "Cheapest", icon: IndianRupee },
  { key: "least_transfers", label: "Least Transfers", icon: ArrowLeftRight },
  { key: "best_availability", label: "Best Availability", icon: ShieldCheck },
];

export function FilterPanel() {
  const { filterPreset, setFilterPreset } = useSearchStore();

  return (
    <div className="flex items-center gap-2 overflow-x-auto pb-1">
      <span className="shrink-0 text-xs font-semibold uppercase tracking-wider text-gray-400">
        Sort:
      </span>
      {PRESETS.map((preset) => {
        const isActive = filterPreset === preset.key;
        return (
          <button
            key={preset.key}
            type="button"
            onClick={() => setFilterPreset(preset.key)}
            className={cn(
              "shrink-0 flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition-all",
              isActive
                ? "bg-[--rr-green-600] text-white shadow-sm"
                : "border border-gray-200 bg-white text-gray-600 hover:border-[--rr-green-300] hover:text-[--rr-green-700]"
            )}
          >
            <preset.icon className="size-3.5" />
            {preset.label}
          </button>
        );
      })}
    </div>
  );
}
