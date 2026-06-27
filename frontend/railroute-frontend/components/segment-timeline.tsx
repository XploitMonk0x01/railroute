"use client";

import { TrainBadge } from "@/components/train-badge";
import { AvailabilityIndicator } from "@/components/availability-indicator";
import type { RouteSegment } from "@/lib/types";
import { Clock, ArrowRight, Timer, MapPin, Ruler } from "lucide-react";
import { formatDuration, formatFare, formatTime } from "@/lib/format";

interface SegmentTimelineProps {
  segments: RouteSegment[];
  compact?: boolean;
}

export function SegmentTimeline({ segments, compact = false }: SegmentTimelineProps) {
  return (
    <div className="flex flex-col gap-4">
      {segments.map((segment, idx) => (
        <div key={`${segment.train_number}-${idx}`}>
          {/* Transfer waiting indicator */}
          {segment.is_transfer && segment.wait_min > 0 && (
            <div className="mb-3 ml-3 flex items-center gap-2">
              <div className="h-6 w-px bg-gradient-to-b from-gray-200 to-amber-300 ml-3" />
              <div className="flex items-center gap-2 rounded-full bg-amber-50 border border-amber-200 px-3 py-1">
                <Timer className="size-3.5 text-amber-600" />
                <span className="text-xs font-semibold text-amber-700">
                  {formatDuration(segment.wait_min)} transfer wait at {segment.from}
                </span>
              </div>
            </div>
          )}

          {/* Segment card */}
          <div className="rounded-xl border border-gray-100 bg-white overflow-hidden">
            {/* Train header bar */}
            <div className="flex items-center justify-between gap-3 border-b border-gray-50 bg-gray-50/80 px-4 py-2.5">
              <div className="flex items-center gap-2.5 min-w-0">
                <span className="font-display text-sm font-bold text-[--rr-green-700]">
                  {segment.train_number}
                </span>
                <span className="text-sm font-medium text-gray-600 truncate">
                  {segment.train_name}
                </span>
                <TrainBadge type={segment.train_type as string} />
              </div>
              <AvailabilityIndicator availability={segment.availability} />
            </div>

            {/* Journey timeline */}
            <div className="px-4 py-4">
              <div className="flex items-start gap-4">
                {/* Departure */}
                <div className="flex flex-col items-start min-w-[90px]">
                  <span className="font-display text-2xl font-bold text-gray-900 leading-none">
                    {formatTime(segment.departure)}
                  </span>
                  <div className="mt-1 flex items-center gap-1">
                    <MapPin className="size-3 text-[--rr-green-500] shrink-0" />
                    <span className="text-xs font-bold text-[--rr-green-700]">{segment.from}</span>
                  </div>
                  {!compact && segment.from_name && (
                    <span className="mt-0.5 text-[11px] text-gray-400 truncate max-w-[100px]">
                      {segment.from_name}
                    </span>
                  )}
                  {segment.day > 1 && (
                    <span className="mt-1 text-[10px] font-semibold text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded">
                      Day {segment.day}
                    </span>
                  )}
                </div>

                {/* Duration spine */}
                <div className="flex flex-1 flex-col items-center gap-1 pt-1">
                  <div className="flex items-center gap-1.5 text-xs text-gray-500">
                    <Clock className="size-3" />
                    <span className="font-medium">{formatDuration(segment.duration_min)}</span>
                  </div>
                  {/* Animated track line */}
                  <div className="relative flex w-full items-center">
                    <div className="h-0.5 w-full bg-gradient-to-r from-[--rr-green-400] to-emerald-400 rounded-full" />
                    <ArrowRight className="absolute right-0 size-3 text-emerald-500 -mr-1" />
                  </div>
                  {!compact && segment.distance_km > 0 && (
                    <div className="flex items-center gap-1 text-[10px] text-gray-400">
                      <Ruler className="size-3" />
                      {segment.distance_km} km
                    </div>
                  )}
                </div>

                {/* Arrival */}
                <div className="flex flex-col items-end min-w-[90px]">
                  <span className="font-display text-2xl font-bold text-gray-900 leading-none">
                    {formatTime(segment.arrival)}
                  </span>
                  <div className="mt-1 flex items-center gap-1">
                    <span className="text-xs font-bold text-[--rr-green-700]">{segment.to}</span>
                    <MapPin className="size-3 text-[--rr-green-500] shrink-0" />
                  </div>
                  {!compact && segment.to_name && (
                    <span className="mt-0.5 text-[11px] text-gray-400 truncate max-w-[100px] text-right">
                      {segment.to_name}
                    </span>
                  )}
                </div>
              </div>

              {/* Fare / class row */}
              <div className="mt-3 flex items-center justify-between border-t border-gray-50 pt-3">
                <div className="flex items-center gap-2.5">
                  <span className="font-display text-base font-bold text-gray-900">
                    {formatFare(segment.fare)}
                  </span>
                  <span className="rounded-md bg-[--rr-green-50] border border-[--rr-green-100] px-2 py-0.5 text-[11px] font-bold text-[--rr-green-700] uppercase tracking-wide">
                    {segment.class}
                  </span>
                </div>
                <div className="text-xs text-gray-400 font-medium">
                  per person
                </div>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
