"use client";

import { SearchForm } from "@/components/search-form";
import { Train, CheckCircle2, TrendingUp, ShieldCheck, ArrowRight, MapPin } from "lucide-react";

// Brand color constants — used inline since Tailwind v4 CSS variables need @theme
const GREEN_800 = "#1e4d3a";
const GREEN_700 = "#226646";
const GREEN_600 = "#2d7f54";
const GREEN_500 = "#339966";
const GREEN_200 = "#a3d9b8";
const GREEN_100 = "#e6f5ed";
const GREEN_50  = "#f2fbf6";
const SAFFRON_500 = "#f07d00";
const SAFFRON_400 = "#ff8f1f";
const SLATE_50 = "#f9fafb";

const STATS = [
  { value: "8,500+", label: "Stations" },
  { value: "12,000+", label: "Trains" },
  { value: "1.2M+", label: "Routes Found" },
  { value: "<2s", label: "Avg. Search Time" },
];

const FEATURES = [
  {
    icon: Train,
    title: "Multi-Hop Route Discovery",
    description:
      "Our graph engine finds alternative routes with 1–3 transfers when your direct train is sold out or waitlisted.",
    color: "bg-emerald-50 text-emerald-700",
  },
  {
    icon: TrendingUp,
    title: "Smart Route Scoring",
    description:
      "Routes ranked by travel time, fare, transfers, and seat availability — customisable to your priorities.",
    color: "bg-amber-50 text-amber-700",
  },
  {
    icon: ShieldCheck,
    title: "Waitlist Monitoring",
    description:
      "Set alerts on any route. Get notified the moment a confirmed seat opens up on your preferred train.",
    color: "bg-sky-50 text-sky-700",
  },
];

const POPULAR_ROUTES = [
  { from: "New Delhi", fromCode: "NDLS", to: "Mumbai", toCode: "CSTM" },
  { from: "Ahmedabad", fromCode: "ADI", to: "New Delhi", toCode: "NDLS" },
  { from: "Bangalore", fromCode: "SBC", to: "Chennai", toCode: "MAS" },
  { from: "Kolkata", fromCode: "HWH", to: "Patna", toCode: "PNBE" },
  { from: "Hyderabad", fromCode: "SC", to: "Mumbai", toCode: "CSTM" },
  { from: "Pune", fromCode: "PUNE", to: "Goa", toCode: "MAO" },
];

export function HeroSection() {
  return (
    <div style={{ background: SLATE_50 }}>
      {/* ── Hero Banner ── */}
      <section
        className="relative overflow-hidden"
        style={{ background: GREEN_800 }}
      >
        {/* Background cross-hatch texture */}
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C%2Fsvg%3E")`,
          }}
        />
        {/* Decorative train-track line */}
        <div
          className="absolute bottom-0 left-0 right-0 h-1.5 opacity-25"
          style={{
            backgroundImage: `repeating-linear-gradient(90deg, ${SAFFRON_400}, ${SAFFRON_400} 6px, transparent 6px, transparent 14px)`,
          }}
        />

        <div className="relative mx-auto max-w-7xl px-4 pt-14 pb-10 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-3xl text-center">

            {/* Headline */}
            <h1
              className="font-display text-4xl font-bold leading-tight tracking-tight sm:text-5xl lg:text-[3.5rem]"
              style={{ color: "#ffffff" }}
            >
              Can&apos;t Get a Ticket?{" "}
              <span style={{ color: SAFFRON_400 }}>We Find a Way.</span>
            </h1>
            <p
              className="mt-5 text-base leading-relaxed sm:text-lg max-w-2xl mx-auto"
              style={{ color: "rgba(255,255,255,0.72)" }}
            >
              Direct train sold out or on waitlist? RailRoute AI discovers smart
              multi-hop alternatives across Indian Railways — scored, ranked, and
              ready in under 2 seconds.
            </p>
          </div>

          {/* Search Form */}
          <div className="mx-auto mt-10 max-w-4xl">
            <SearchForm variant="hero" />
          </div>

          {/* Stats strip */}
          <div className="mt-10 flex flex-wrap items-center justify-center gap-x-10 gap-y-4">
            {STATS.map((stat) => (
              <div key={stat.label} className="text-center">
                <div className="font-display text-2xl font-bold" style={{ color: "#fff" }}>{stat.value}</div>
                <div className="text-xs font-medium mt-0.5" style={{ color: "rgba(255,255,255,0.55)" }}>{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Popular Routes ── */}
      <section className="border-b border-gray-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-5 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3 overflow-x-auto pb-1 no-scrollbar">
            <span className="shrink-0 text-xs font-semibold uppercase tracking-wider text-gray-400">
              Popular:
            </span>
            {POPULAR_ROUTES.map((route) => (
              <a
                key={`${route.fromCode}-${route.toCode}`}
                href={`/search?from=${route.fromCode}&to=${route.toCode}&date=${new Date(Date.now() + 86400000).toISOString().split("T")[0]}&class=3A`}
                className="shrink-0 flex items-center gap-1.5 rounded-full border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs font-medium text-gray-600 hover:border-[--rr-green-300] hover:bg-[--rr-green-50] hover:text-[--rr-green-700] transition-colors"
              >
                <span>{route.from}</span>
                <ArrowRight className="size-3 text-gray-400" />
                <span>{route.to}</span>
              </a>
            ))}
          </div>
        </div>
      </section>

      {/* ── How It Works ── */}
      <section className="py-16 sm:py-20" style={{ background: GREEN_50 }}>
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mb-12 text-center">
            <h2 className="font-display text-2xl font-bold tracking-tight text-gray-900 sm:text-3xl">
              How RailRoute AI Works
            </h2>
            <p className="mt-2 text-sm text-gray-500">
              Three steps from search to seat
            </p>
          </div>

          <div className="relative grid grid-cols-1 gap-8 md:grid-cols-3">
            {/* Connector line on md+ */}
            <div
              className="absolute top-10 left-[33%] right-[33%] hidden h-px md:block"
              style={{ backgroundImage: `linear-gradient(to right, ${GREEN_200}, ${GREEN_500}, ${GREEN_200})` }}
            />

            {[
              {
                step: "01",
                title: "Enter Your Journey",
                desc: "Pick source, destination, travel date and preferred class.",
              },
              {
                step: "02",
                title: "AI Finds Routes",
                desc: "Our NetworkX graph engine explores thousands of combinations in milliseconds.",
              },
              {
                step: "03",
                title: "Pick & Track",
                desc: "Choose your best route and set up alerts for availability changes.",
              },
            ].map((item, idx) => (
              <div key={item.step} className="relative flex flex-col items-center text-center">
                <div
                  className="mb-4 flex size-20 items-center justify-center rounded-full bg-white shadow-sm"
                  style={{ border: `2px solid ${GREEN_200}` }}
                >
                  <span
                    className="font-display text-2xl font-bold"
                    style={{ color: GREEN_600 }}
                  >
                    {item.step}
                  </span>
                </div>
                <h3 className="font-display text-base font-semibold text-gray-900 mb-1.5">
                  {item.title}
                </h3>
                <p className="text-sm text-gray-600 leading-relaxed max-w-xs">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section className="py-16 sm:py-20 bg-white border-t border-gray-200">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mb-12 border-b border-gray-200 pb-5">
            <h2 className="font-display text-2xl font-bold tracking-tight text-gray-900 sm:text-3xl">
              Why Choose RailRoute AI
            </h2>
          </div>
          <div className="grid grid-cols-1 gap-10 md:grid-cols-3">
            {FEATURES.map((f, idx) => (
              <div key={f.title} className="flex flex-col">
                <div className="flex items-center gap-3 mb-3">
                  <div className="flex size-10 items-center justify-center bg-gray-100 text-gray-700">
                    <f.icon className="size-5" />
                  </div>
                  <h3 className="font-display text-lg font-bold text-gray-900">
                    {f.title}
                  </h3>
                </div>
                <p className="text-sm text-gray-600 leading-relaxed pl-13">
                  {f.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Trust Banner ── */}
      <section className="border-t border-b border-gray-200 bg-gray-50 py-8">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center justify-center gap-x-12 gap-y-4 text-sm text-gray-600">
            {[
              "No IRCTC login required to search",
              "100% Free to use",
              "Real-time waitlist updates",
              "Instant alternative routing",
            ].map((text) => (
              <div key={text} className="flex items-center gap-2.5">
                <div className="size-1.5 rounded-full bg-gray-400" />
                <span className="font-medium text-gray-700">{text}</span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
