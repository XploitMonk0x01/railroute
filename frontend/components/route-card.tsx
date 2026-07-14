"use client";

import { useState } from "react";
import { SegmentTimeline } from "@/components/segment-timeline";
import type { RouteResult } from "@/lib/types";
import { Clock, IndianRupee, ArrowLeftRight, Timer, ChevronDown, Star } from "lucide-react";
import { formatDuration, formatFare } from "@/lib/format";
import { cn } from "@/lib/utils";

interface RouteCardProps {
  route: RouteResult;
  rank: number;
}

export function RouteCard({ route, rank }: RouteCardProps) {
  const [expanded, setExpanded] = useState(false);

  const scoreLabel =
    route.score <= 0.35 ? "Excellent" :
    route.score <= 0.5  ? "Good" :
    route.score <= 0.65 ? "Fair" : "OK";

  const scoreBadgeClass =
    route.score <= 0.35 ? "bg-emerald-50 text-emerald-700 border-emerald-200" :
    route.score <= 0.5  ? "bg-sky-50 text-sky-700 border-sky-200" :
    route.score <= 0.65 ? "bg-amber-50 text-amber-700 border-amber-200" :
                          "bg-orange-50 text-orange-700 border-orange-200";

  const first = route.segments[0];
  const last = route.segments[route.segments.length - 1];

  return (
    <div
      className={cn(
        "rounded-xl border bg-white overflow-hidden transition-all duration-200",
        expanded ? "border-[--rr-green-300] shadow-md shadow-[--rr-green-600]/5" : "border-gray-200 hover:border-gray-300 hover:shadow-sm"
      )}
    >
      {/* Ticket-stub top accent for rank 1 */}
      {rank === 1 && (
        <div className="h-1 w-full bg-gradient-to-r from-[--rr-green-500] via-[--rr-green-400] to-emerald-400" />
      )}

      {/* Collapse header */}
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left px-4 py-4 sm:px-5 hover:bg-gray-50/70 transition-colors"
      >
        <div className="flex items-center gap-3">
          {/* Rank badge */}
          <div
            className={cn(
              "flex size-8 shrink-0 items-center justify-center rounded-lg text-xs font-bold",
              rank === 1
                ? "bg-[--rr-green-600] text-white"
                : "bg-gray-100 text-gray-500"
            )}
          >
            {rank === 1 ? <Star className="size-3.5 fill-white text-white" /> : `#${rank}`}
          </div>

          {/* Route overview */}
          <div className="flex items-center gap-2 min-w-0">
            <span className="font-display text-base font-bold text-gray-900">{first?.from}</span>
            <span className="text-gray-300">→</span>
            <span className="font-display text-base font-bold text-gray-900">{last?.to}</span>
          </div>

          {/* Stats chips */}
          <div className="ml-auto flex items-center flex-wrap gap-x-4 gap-y-1 shrink-0">
            <div className="flex items-center gap-1.5 text-sm text-gray-600">
              <Clock className="size-3.5 text-gray-400" />
              <span className="font-semibold text-gray-900">{formatDuration(route.total_time_min)}</span>
            </div>
            <div className="flex items-center gap-1.5 text-sm text-gray-600">
              <IndianRupee className="size-3.5 text-gray-400" />
              <span className="font-semibold text-gray-900">{formatFare(route.total_fare).replace("₹","")}</span>
            </div>
            <div className="flex items-center gap-1.5 text-sm text-gray-600 hidden sm:flex">
              <ArrowLeftRight className="size-3.5 text-gray-400" />
              <span className="font-medium text-gray-700">
                {route.transfer_count} {route.transfer_count === 1 ? "transfer" : "transfers"}
              </span>
            </div>
            {route.total_wait_min > 0 && (
              <div className="hidden items-center gap-1.5 text-xs text-gray-500 lg:flex">
                <Timer className="size-3.5" />
                {formatDuration(route.total_wait_min)} wait
              </div>
            )}

            {/* Score badge */}
            <span className={cn("rounded-full border px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wide", scoreBadgeClass)}>
              {scoreLabel}
            </span>

            {/* Expand caret */}
            <ChevronDown
              className={cn(
                "size-4 text-gray-400 transition-transform duration-200 shrink-0",
                expanded && "rotate-180"
              )}
            />
          </div>
        </div>

        {/* Segment preview row — departure / arrival times */}
        <div className="mt-3 ml-11 flex items-center gap-2 overflow-x-auto pb-1">
          {route.segments.map((seg, i) => (
            <div key={i} className="flex items-center gap-2 shrink-0">
              {i > 0 && (
                <div className="flex items-center gap-1 rounded-full bg-amber-50 border border-amber-200 px-2 py-0.5">
                  <Timer className="size-2.5 text-amber-600" />
                  <span className="text-[10px] font-medium text-amber-700">Transfer</span>
                </div>
              )}
              <div className="rounded-lg bg-gray-50 border border-gray-100 px-2.5 py-1.5">
                <div className="text-[10px] font-semibold text-[--rr-green-600] uppercase tracking-wide">{seg.train_number}</div>
                <div className="text-xs font-bold text-gray-800">{seg.from} → {seg.to}</div>
              </div>
            </div>
          ))}
        </div>
      </button>

      {/* Ticket tear line divider */}
      {expanded && (
        <div className="relative px-5">
          <div className="flex items-center gap-2">
            <div className="-ml-5 size-4 rounded-full bg-gray-50 border-r border-t border-b border-gray-200" />
            <div className="flex-1 border-t border-dashed border-gray-200" />
            <div className="-mr-5 size-4 rounded-full bg-gray-50 border-l border-t border-b border-gray-200" />
          </div>
        </div>
      )}

      {/* Expanded timeline */}
      <div
        className={cn(
          "overflow-hidden transition-all duration-300 ease-in-out",
          expanded ? "max-h-[1200px] opacity-100" : "max-h-0 opacity-0"
        )}
      >
        <div className="px-4 py-5 sm:px-5">
          <SegmentTimeline segments={route.segments} />
        </div>
      </div>
    </div>
  );
}
