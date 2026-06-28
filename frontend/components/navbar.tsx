"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  TrainFront,
  Search,
  Bell,
  Menu,
  X,
  LogIn,
  User,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { href: "/", label: "Home" },
  { href: "/search", label: "Search Routes" },
  { href: "/watchlist", label: "Watchlist" },
];

export function Navbar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={cn(
        "sticky top-0 z-50 w-full transition-all duration-200",
        scrolled
          ? "bg-white shadow-sm shadow-black/5 border-b border-gray-100"
          : "bg-white border-b border-gray-100"
      )}
    >
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 group shrink-0">
          <div className="flex size-8 items-center justify-center rounded-lg bg-[--rr-green-700] transition-colors group-hover:bg-[--rr-green-800]">
            <TrainFront className="size-4 text-white" />
          </div>
          <span className="font-display text-lg font-bold tracking-tight text-gray-900">
            Rail<span className="text-[--rr-green-600]">Route</span>
            <span className="ml-1 text-xs font-semibold text-[--rr-saffron-500] align-super">AI</span>
          </span>
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden items-center gap-0.5 md:flex">
          {NAV_LINKS.map((link) => {
            const isActive =
              pathname === link.href ||
              (link.href !== "/" && pathname.startsWith(link.href));
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "relative px-4 py-2 text-sm font-medium transition-colors rounded-md",
                  isActive
                    ? "text-[--rr-green-700] bg-[--rr-green-50]"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                )}
              >
                {link.label}
                {isActive && (
                  <span className="absolute bottom-0.5 left-4 right-4 h-0.5 rounded-full bg-[--rr-green-500]" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Right Actions */}
        <div className="flex items-center gap-2">
          <Link href="/login" className="hidden md:block">
            <Button
              variant="ghost"
              size="sm"
              className="gap-1.5 text-gray-600 hover:text-gray-900 hover:bg-gray-50 font-medium text-sm"
            >
              <LogIn className="size-4" />
              Sign In
            </Button>
          </Link>
          <Link href="/signup" className="hidden md:block">
            <Button
              size="sm"
              className="gap-1.5 bg-[--rr-green-600] hover:bg-[--rr-green-700] text-white font-semibold text-sm shadow-none"
            >
              Get Started
            </Button>
          </Link>

          {/* Mobile Toggle */}
          <button
            type="button"
            className="flex md:hidden size-9 items-center justify-center rounded-lg text-gray-600 hover:bg-gray-100 transition-colors"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="Toggle menu"
          >
            {mobileOpen ? <X className="size-5" /> : <Menu className="size-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Nav */}
      {mobileOpen && (
        <div className="border-t border-gray-100 bg-white px-4 pb-4 md:hidden animate-slide-up">
          <nav className="flex flex-col gap-0.5 pt-3">
            {NAV_LINKS.map((link) => {
              const isActive =
                pathname === link.href ||
                (link.href !== "/" && pathname.startsWith(link.href));
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileOpen(false)}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-[--rr-green-50] text-[--rr-green-700]"
                      : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                  )}
                >
                  {link.label}
                </Link>
              );
            })}
            <div className="mt-2 flex flex-col gap-2 pt-2 border-t border-gray-100">
              <Link href="/login" onClick={() => setMobileOpen(false)}>
                <Button variant="outline" size="sm" className="w-full gap-2 text-sm">
                  <LogIn className="size-4" /> Sign In
                </Button>
              </Link>
              <Link href="/signup" onClick={() => setMobileOpen(false)}>
                <Button
                  size="sm"
                  className="w-full bg-[--rr-green-600] hover:bg-[--rr-green-700] text-white text-sm"
                >
                  Get Started
                </Button>
              </Link>
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
