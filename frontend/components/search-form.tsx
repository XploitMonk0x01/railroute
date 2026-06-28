"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { StationSelector } from "@/components/station-selector";
import { useSearchStore } from "@/store/search-store";
import { ArrowLeftRight, CalendarDays, Search, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

const CLASSES = [
  { value: "SL", label: "Sleeper (SL)" },
  { value: "3A", label: "Third AC (3A)" },
  { value: "2A", label: "Second AC (2A)" },
  { value: "1A", label: "First AC (1A)" },
  { value: "CC", label: "Chair Car (CC)" },
  { value: "EC", label: "Exec. Chair (EC)" },
];

interface SearchFormProps {
  variant?: "hero" | "compact";
}

export function SearchForm({ variant = "hero" }: SearchFormProps) {
  const router = useRouter();
  const store = useSearchStore();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [classOpen, setClassOpen] = useState(false);

  const isHero = variant === "hero";
  const today = new Date().toISOString().split("T")[0];
  const selectedClass = CLASSES.find((c) => c.value === store.travelClass) ?? CLASSES[1];

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!store.source || !store.destination || !store.date) return;
    setIsSubmitting(true);
    const params = new URLSearchParams({
      from: store.source,
      to: store.destination,
      date: store.date,
      class: store.travelClass,
    });
    router.push(`/search?${params.toString()}`);
  }

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div
        className={cn(
          "rounded-2xl bg-white shadow-xl shadow-black/10",
          isHero ? "p-5 sm:p-6" : "p-4 border border-gray-100"
        )}
      >
        {/* Main search row */}
        <div className="flex flex-col gap-3 lg:flex-row lg:items-stretch">
          {/* FROM */}
          <div className="flex-1 min-w-0">
            <StationSelector
              value={store.source}
              displayValue={store.sourceName}
              onSelect={store.setSource}
              placeholder="From — City or Station"
              label="From"
              id="station-from"
            />
          </div>

          {/* Swap */}
          <div className="flex items-end justify-center lg:items-center lg:px-0">
            <button
              type="button"
              onClick={store.swapStations}
              className="flex size-9 items-center justify-center rounded-full border-2 border-gray-200 bg-white text-gray-500 hover:border-[--rr-green-400] hover:text-[--rr-green-600] transition-all hover:rotate-180 duration-300"
              aria-label="Swap stations"
            >
              <ArrowLeftRight className="size-4" />
            </button>
          </div>

          {/* TO */}
          <div className="flex-1 min-w-0">
            <StationSelector
              value={store.destination}
              displayValue={store.destinationName}
              onSelect={store.setDestination}
              placeholder="To — City or Station"
              label="To"
              id="station-to"
            />
          </div>

          {/* DATE */}
          <div className="lg:w-44">
            <label className="block text-[11px] font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
              Date
            </label>
            <div className="relative">
              <CalendarDays className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-gray-400" />
              <input
                id="journey-date"
                type="date"
                value={store.date}
                onChange={(e) => store.setDate(e.target.value)}
                min={today}
                required
                className="h-11 w-full rounded-lg border border-gray-200 bg-white pl-9 pr-3 text-sm font-medium text-gray-900 focus:border-[--rr-green-400] focus:outline-none focus:ring-2 focus:ring-[--rr-green-400]/20 transition-colors"
              />
            </div>
          </div>

          {/* CLASS — custom dropdown */}
          <div className="lg:w-40 relative">
            <label className="block text-[11px] font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
              Class
            </label>
            <button
              type="button"
              id="travel-class"
              onClick={() => setClassOpen(!classOpen)}
              className="flex h-11 w-full items-center justify-between rounded-lg border border-gray-200 bg-white px-3 text-sm font-medium text-gray-900 hover:border-[--rr-green-400] focus:outline-none focus:ring-2 focus:ring-[--rr-green-400]/20 transition-colors"
            >
              <span>{selectedClass.value}</span>
              <div className="flex flex-col gap-px">
                <span className="text-[10px] text-gray-400 leading-none">{selectedClass.label.split("(")[0].trim()}</span>
              </div>
              <ChevronDown className={cn("size-4 text-gray-400 transition-transform", classOpen && "rotate-180")} />
            </button>
            {classOpen && (
              <div className="absolute top-full left-0 right-0 z-50 mt-1 rounded-xl border border-gray-100 bg-white shadow-xl animate-slide-up">
                {CLASSES.map((cls) => (
                  <button
                    key={cls.value}
                    type="button"
                    onClick={() => { store.setTravelClass(cls.value); setClassOpen(false); }}
                    className={cn(
                      "flex w-full items-center gap-3 px-3 py-2.5 text-sm transition-colors first:rounded-t-xl last:rounded-b-xl",
                      store.travelClass === cls.value
                        ? "bg-[--rr-green-50] text-[--rr-green-700] font-semibold"
                        : "text-gray-700 hover:bg-gray-50"
                    )}
                  >
                    <span className="w-8 rounded bg-gray-100 px-1.5 py-0.5 text-center text-[10px] font-bold text-gray-600">
                      {cls.value}
                    </span>
                    <span>{cls.label}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Search Button */}
        <div className={cn("flex justify-center", isHero ? "mt-6" : "mt-5")}>
          <button
            type="submit"
            disabled={!store.source || !store.destination || !store.date || isSubmitting}
            className="flex h-12 w-full md:w-auto min-w-[200px] items-center justify-center gap-2 rounded bg-[#f07d00] px-8 text-sm font-bold text-white hover:bg-[#d46b00] disabled:opacity-50 disabled:cursor-not-allowed transition-colors uppercase tracking-wider"
          >
            {isSubmitting ? (
              <span className="size-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
            ) : (
              <Search className="size-4" />
            )}
            Search Trains
          </button>
        </div>
      </div>
    </form>
  );
}
