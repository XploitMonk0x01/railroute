"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { getWatchlist, deleteWatchlistEntry } from "@/lib/api";
import type { WatchlistEntry } from "@/lib/types";
import {
  Bell,
  Trash2,
  MapPin,
  CalendarDays,
  ArrowRight,
  Eye,
  EyeOff,
  Plus,
} from "lucide-react";
import Link from "next/link";

export default function WatchlistPage() {
  const [entries, setEntries] = useState<WatchlistEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await getWatchlist();
        setEntries(data);
      } catch {
        // Handle error
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, []);

  async function handleDelete(id: number) {
    try {
      await deleteWatchlistEntry(id);
      setEntries((prev) => prev.filter((e) => e.id !== id));
    } catch {
      // Handle error
    }
  }

  const active = entries.filter((e) => e.is_active);
  const inactive = entries.filter((e) => !e.is_active);

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
            Watchlist
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Monitor routes and get notified when seats become available
          </p>
        </div>
        <Link href="/search">
          <Button className="gap-2 bg-gradient-to-r from-indigo-500 to-cyan-500 text-white shadow-lg shadow-indigo-500/25">
            <Plus className="size-4" />
            New Search
          </Button>
        </Link>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex flex-col gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full rounded-xl" />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && entries.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="size-16 rounded-full bg-muted flex items-center justify-center mb-4">
            <Bell className="size-7 text-muted-foreground" />
          </div>
          <h2 className="text-lg font-semibold mb-1">No watchlist items</h2>
          <p className="text-sm text-muted-foreground max-w-md mb-6">
            Search for a route and add it to your watchlist to monitor seat
            availability and get notified.
          </p>
          <Link href="/search">
            <Button variant="outline" className="gap-2">
              <Plus className="size-4" />
              Search Routes
            </Button>
          </Link>
        </div>
      )}

      {/* Active entries */}
      {active.length > 0 && (
        <div className="flex flex-col gap-3 mb-8">
          <div className="flex items-center gap-2 mb-1">
            <Eye className="size-4 text-emerald-400" />
            <span className="text-sm font-semibold">Active Monitoring</span>
            <Badge variant="secondary" className="text-xs">
              {active.length}
            </Badge>
          </div>

          {active.map((entry) => (
            <WatchlistCard
              key={entry.id}
              entry={entry}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      {/* Inactive entries */}
      {inactive.length > 0 && (
        <div className="flex flex-col gap-3">
          <Separator className="mb-2" />
          <div className="flex items-center gap-2 mb-1">
            <EyeOff className="size-4 text-muted-foreground" />
            <span className="text-sm font-semibold text-muted-foreground">
              Inactive
            </span>
            <Badge variant="secondary" className="text-xs">
              {inactive.length}
            </Badge>
          </div>

          {inactive.map((entry) => (
            <WatchlistCard
              key={entry.id}
              entry={entry}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function WatchlistCard({
  entry,
  onDelete,
}: {
  entry: WatchlistEntry;
  onDelete: (id: number) => void;
}) {
  const statusColor = entry.latest_status?.includes("available")
    ? "text-emerald-400"
    : entry.latest_status?.includes("Expired")
      ? "text-muted-foreground"
      : "text-amber-400";

  return (
    <Card
      className={`border-border/50 bg-card/50 backdrop-blur-sm transition-all hover:border-border/80 hover:shadow-md ${!entry.is_active ? "opacity-60" : ""}`}
    >
      <CardContent className="p-4 sm:p-5">
        <div className="flex items-start justify-between gap-4">
          {/* Route info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <div className="flex items-center gap-2">
                <MapPin className="size-3.5 text-indigo-400 shrink-0" />
                <span className="text-sm font-bold">{entry.source_code}</span>
                <ArrowRight className="size-3 text-muted-foreground" />
                <span className="text-sm font-bold">
                  {entry.destination_code}
                </span>
              </div>
              <Badge
                variant="outline"
                className="text-[10px] uppercase font-medium"
              >
                {entry.preferred_class}
              </Badge>
            </div>

            <div className="flex items-center gap-3 text-xs text-muted-foreground mb-2">
              <div className="flex items-center gap-1">
                <CalendarDays className="size-3" />
                {entry.journey_date}
              </div>
              <span>•</span>
              <span>Budget: ₹{entry.max_budget}</span>
            </div>

            {/* Status */}
            {entry.latest_status && (
              <p className={`text-xs font-medium ${statusColor}`}>
                {entry.latest_status}
              </p>
            )}

            {/* Notification types */}
            <div className="mt-2 flex flex-wrap gap-1.5">
              {entry.notify_on.map((type) => (
                <Badge
                  key={type}
                  variant="secondary"
                  className="text-[10px]"
                >
                  {type.replace("_", " ")}
                </Badge>
              ))}
            </div>
          </div>

          {/* Delete button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(entry.id)}
            className="shrink-0 text-muted-foreground hover:text-destructive"
            aria-label="Delete watchlist entry"
          >
            <Trash2 className="size-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
