"use client";

import { useState, useEffect, useRef } from "react";
import { MapPin, Train, X } from "lucide-react";
import { getStations } from "@/lib/api";
import type { Station } from "@/lib/types";
import { cn } from "@/lib/utils";

interface StationSelectorProps {
  value: string;
  displayValue: string;
  onSelect: (code: string, name: string) => void;
  placeholder?: string;
  label?: string;
  id?: string;
}

export function StationSelector({
  value,
  displayValue,
  onSelect,
  placeholder = "Search station...",
  label,
  id,
}: StationSelectorProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Station[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (query.length < 1) { setResults([]); return; }
    setIsLoading(true);
    const t = setTimeout(async () => {
      try {
        setResults(await getStations(query));
        setHighlightIndex(-1);
      } catch { setResults([]); }
      finally { setIsLoading(false); }
    }, 150);
    return () => clearTimeout(t);
  }, [query]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function handleSelect(station: Station) {
    onSelect(station.code, station.name);
    setQuery("");
    setIsOpen(false);
    setResults([]);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!isOpen || results.length === 0) return;
    if (e.key === "ArrowDown") { e.preventDefault(); setHighlightIndex((i) => Math.min(i + 1, results.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setHighlightIndex((i) => Math.max(i - 1, 0)); }
    else if (e.key === "Enter" && highlightIndex >= 0) { e.preventDefault(); handleSelect(results[highlightIndex]); }
    else if (e.key === "Escape") { setIsOpen(false); }
  }

  return (
    <div ref={containerRef} className="relative w-full">
      {label && (
        <label htmlFor={id} className="block text-[11px] font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
          {label}
        </label>
      )}

      {/* Selected station display OR search input */}
      {value && !isOpen ? (
        <button
          type="button"
          onClick={() => { setIsOpen(true); setTimeout(() => inputRef.current?.focus(), 50); }}
          className="flex h-11 w-full items-center gap-2.5 rounded-lg border border-gray-200 bg-white px-3 text-left transition-colors hover:border-[--rr-green-400]"
        >
          <MapPin className="size-4 text-[--rr-green-500] shrink-0" />
          <div className="min-w-0 flex-1">
            <div className="text-sm font-bold text-gray-900 leading-tight">{value}</div>
            <div className="text-xs text-gray-400 truncate">{displayValue}</div>
          </div>
          <X
            className="size-3.5 text-gray-300 hover:text-gray-500 shrink-0 transition-colors"
            onClick={(e) => { e.stopPropagation(); onSelect("", ""); }}
          />
        </button>
      ) : (
        <div className="relative">
          <MapPin className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-gray-400" />
          <input
            ref={inputRef}
            id={id}
            type="text"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setIsOpen(true); }}
            onFocus={() => query.length >= 1 && setIsOpen(true)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            autoComplete="off"
            className="h-11 w-full rounded-lg border border-gray-200 bg-white pl-9 pr-3 text-sm text-gray-900 placeholder:text-gray-400 focus:border-[--rr-green-400] focus:outline-none focus:ring-2 focus:ring-[--rr-green-400]/20 transition-colors"
          />
          {isLoading && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              <div className="size-4 rounded-full border-2 border-gray-200 border-t-[--rr-green-500] animate-spin" />
            </div>
          )}
        </div>
      )}

      {/* Dropdown */}
      {isOpen && (query.length >= 1 || results.length > 0) && (
        <div className="absolute z-50 mt-1 w-full rounded-xl border border-gray-100 bg-white shadow-xl shadow-black/8 overflow-hidden animate-slide-up">
          {results.length === 0 && !isLoading ? (
            <div className="px-4 py-6 text-center text-sm text-gray-400">No stations found</div>
          ) : (
            <div className="max-h-64 overflow-y-auto">
              {results.map((station, idx) => (
                <button
                  key={station.code}
                  type="button"
                  onClick={() => handleSelect(station)}
                  className={cn(
                    "flex w-full items-center gap-3 px-3 py-2.5 text-left transition-colors border-b border-gray-50 last:border-0",
                    idx === highlightIndex
                      ? "bg-[--rr-green-50]"
                      : "hover:bg-gray-50"
                  )}
                >
                  <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-[--rr-green-50]">
                    <Train className="size-4 text-[--rr-green-600]" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-gray-900">{station.code}</span>
                      {station.is_junction && (
                        <span className="rounded-full bg-amber-50 border border-amber-200 px-1.5 py-0.5 text-[9px] font-bold text-amber-700 uppercase">
                          Junction
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-gray-500 truncate">
                      {station.name}{station.city ? `, ${station.city}` : ""}
                    </div>
                  </div>
                  {station.score > 100 && (
                    <div className="shrink-0 text-[10px] font-medium text-gray-400">
                      ★ Popular
                    </div>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
