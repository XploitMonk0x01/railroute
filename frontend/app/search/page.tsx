"use client";

import { useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { RouteCard } from "@/components/route-card";
import { FilterPanel } from "@/components/filter-panel";
import { SearchForm } from "@/components/search-form";
import { useSearchStore } from "@/store/search-store";
import { searchRoutes } from "@/lib/api";
import { AlertTriangle, CheckCircle2, XCircle, Train, Loader2 } from "lucide-react";

function SearchResultsContent() {
  const searchParams = useSearchParams();
  const store = useSearchStore();

  const from = searchParams.get("from") || "";
  const to = searchParams.get("to") || "";
  const date = searchParams.get("date") || "";
  const travelClass = searchParams.get("class") || "3A";

  useEffect(() => {
    if (!from || !to || !date) return;
    if (store.source !== from) store.setSource(from, "");
    if (store.destination !== to) store.setDestination(to, "");
    if (store.date !== date) store.setDate(date);
    if (store.travelClass !== travelClass) store.setTravelClass(travelClass);

    async function doSearch() {
      store.setLoading(true);
      try {
        const results = await searchRoutes({ source: from, destination: to, date, class: travelClass });
        store.setResults(results);
      } catch (err) {
        store.setError(err instanceof Error ? err.message : "An error occurred");
      }
    }
    doSearch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [from, to, date, travelClass]);

  const filteredRoutes = store.getFilteredRoutes();
  const hasParams = from && to && date;

  return (
    <div className="min-h-screen bg-[--rr-slate-50]">
      {/* Compact search bar */}
      <div className="border-b border-gray-200 bg-white py-3 shadow-sm">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <SearchForm variant="compact" />
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        {/* No params state */}
        {!hasParams && (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="size-16 rounded-full bg-gray-100 flex items-center justify-center mb-4">
              <Train className="size-7 text-gray-400" />
            </div>
            <h2 className="font-display text-lg font-semibold text-gray-900 mb-1">No search query</h2>
            <p className="text-sm text-gray-500 max-w-md">
              Use the search form above to find train routes between two stations.
            </p>
          </div>
        )}

        {/* Loading state */}
        {hasParams && store.isLoading && (
          <div className="flex flex-col gap-6">
            {/* Header skeleton */}
            <div className="flex items-center gap-3">
              <div className="h-5 w-48 rounded-full bg-gray-200 animate-pulse" />
              <div className="h-5 w-20 rounded-full bg-gray-200 animate-pulse" />
            </div>
            {/* Skeleton cards */}
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="rounded-xl border border-gray-200 bg-white p-5 space-y-3">
                <div className="flex items-center gap-3">
                  <div className="size-8 rounded-lg bg-gray-100 animate-pulse" />
                  <div className="h-5 w-40 rounded bg-gray-100 animate-pulse" />
                  <div className="ml-auto h-5 w-24 rounded bg-gray-100 animate-pulse" />
                </div>
                <div className="ml-11 h-10 rounded-lg bg-gray-50 animate-pulse" />
              </div>
            ))}
          </div>
        )}

        {/* Error state */}
        {store.error && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="size-14 rounded-full bg-red-50 flex items-center justify-center mb-4">
              <XCircle className="size-6 text-red-500" />
            </div>
            <h2 className="font-display text-lg font-semibold text-gray-900 mb-1">Search failed</h2>
            <p className="text-sm text-gray-500 max-w-sm">{store.error}</p>
          </div>
        )}

        {/* Results */}
        {hasParams && !store.isLoading && store.results && (
          <div className="flex flex-col gap-5">
            {/* Direct train banner */}
            <div
              className={`flex items-center gap-3 rounded-xl border px-4 py-3 ${
                store.results.direct_available
                  ? "border-emerald-200 bg-emerald-50"
                  : "border-amber-200 bg-amber-50"
              }`}
            >
              {store.results.direct_available ? (
                <>
                  <CheckCircle2 className="size-5 text-emerald-600 shrink-0" />
                  <div>
                    <span className="text-sm font-semibold text-emerald-800">Direct train available! </span>
                    <span className="text-sm text-emerald-700">See alternative routes below too.</span>
                  </div>
                </>
              ) : (
                <>
                  <AlertTriangle className="size-5 text-amber-600 shrink-0" />
                  <div className="flex-1">
                    <span className="text-sm font-semibold text-amber-800">No direct tickets available </span>
                    <span className="text-sm text-amber-700">for {from} → {to} on {date}</span>
                  </div>
                  <span className="rounded-full bg-amber-600 px-3 py-0.5 text-xs font-bold text-white shrink-0">
                    {filteredRoutes.length} alternatives
                  </span>
                </>
              )}
            </div>

            {/* Filter tabs */}
            <FilterPanel />

            {/* Route count */}
            <div className="flex items-center gap-2">
              <h2 className="font-display text-sm font-semibold text-gray-700">
                {filteredRoutes.length} route{filteredRoutes.length !== 1 ? "s" : ""} found
              </h2>
              <div className="flex-1 h-px bg-gray-200" />
            </div>

            {/* Route cards */}
            <div className="flex flex-col gap-3 stagger">
              {filteredRoutes.length === 0 ? (
                <div className="rounded-xl border border-gray-200 bg-white py-14 text-center">
                  <p className="text-sm text-gray-500">
                    No routes match your current filters. Try adjusting them.
                  </p>
                </div>
              ) : (
                filteredRoutes.map((route, idx) => (
                  <div key={route.route_id} className="animate-slide-up">
                    <RouteCard route={route} rank={idx + 1} />
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[--rr-slate-50]">
          <div className="border-b border-gray-200 bg-white h-20" />
          <div className="mx-auto max-w-7xl px-4 py-8">
            <div className="flex flex-col gap-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-24 rounded-xl bg-white border border-gray-200 animate-pulse" />
              ))}
            </div>
          </div>
        </div>
      }
    >
      <SearchResultsContent />
    </Suspense>
  );
}
