"use client";

import Link from "next/link";
import { TrainFront, Heart, ExternalLink } from "lucide-react";

const LINKS = {
  Product: [
    { href: "/search", label: "Search Routes" },
    { href: "/watchlist", label: "Watchlist" },
    { href: "#", label: "WL Predictor (Soon)", disabled: true },
  ],
  Resources: [
    { href: "#", label: "How It Works" },
    { href: "#", label: "API Docs" },
    { href: "#", label: "Station Index" },
  ],
  Legal: [
    { href: "#", label: "Privacy Policy" },
    { href: "#", label: "Terms of Service" },
    { href: "#", label: "Disclaimer" },
  ],
};

export function Footer() {
  return (
    <footer className="border-t border-gray-100 bg-white">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-5">
          {/* Brand — wider */}
          <div className="col-span-2 md:col-span-2">
            <div className="flex items-center gap-2 mb-4">
              <div className="flex size-8 items-center justify-center bg-gray-900 text-white">
                <TrainFront className="size-4" />
              </div>
              <span className="font-display text-lg font-bold text-gray-900">
                RailRoute
              </span>
            </div>
            <p className="text-sm text-gray-500 leading-relaxed max-w-xs">
              Intelligent alternative route discovery for Indian Railways. Find a path when your
              direct train is sold out.
            </p>
          </div>

          {/* Link columns */}
          {Object.entries(LINKS).map(([title, links]) => (
            <div key={title}>
              <h3 className="text-xs font-bold uppercase tracking-widest text-gray-400 mb-4">{title}</h3>
              <ul className="flex flex-col gap-2.5">
                {links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className={`text-sm transition-colors ${
                        "disabled" in link && link.disabled
                          ? "text-gray-300 cursor-not-allowed"
                          : "text-gray-500 hover:text-[--rr-green-700]"
                      }`}
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-10 flex flex-col items-start justify-between gap-3 border-t border-gray-100 pt-8 sm:flex-row sm:items-center">
          <p className="text-xs text-gray-400">
            © {new Date().getFullYear()} RailRoute AI · Not affiliated with Indian Railways or IRCTC
          </p>
          <div className="flex items-center gap-4 text-xs text-gray-400">
            <span className="flex items-center gap-1">
              Made with <Heart className="size-3 text-red-400 fill-red-400 mx-0.5" /> in India
            </span>
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 hover:text-gray-700 transition-colors"
            >
              <ExternalLink className="size-3" /> GitHub
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
