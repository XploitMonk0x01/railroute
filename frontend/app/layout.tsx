import { Plus_Jakarta_Sans, Space_Grotesk } from "next/font/google"

import "./globals.css"
import { ThemeProvider } from "@/components/theme-provider"
import { TooltipProvider } from "@/components/ui/tooltip"
import { Navbar } from "@/components/navbar"
import { Footer } from "@/components/footer"
import { cn } from "@/lib/utils"

/* Display / heading font — has personality, not generic */
const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["400", "500", "600", "700"],
})

/* Body font — clean, legible, professional */
const plusJakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
  weight: ["400", "500", "600", "700"],
})

export const metadata = {
  title: "RailRoute AI — Smart Train Route Planner for Indian Railways",
  description:
    "Find alternative multi-train routes when direct tickets are unavailable. AI-powered route discovery across 8,000+ stations and 12,000+ trains on Indian Railways.",
  keywords: [
    "Indian Railways",
    "train route planner",
    "alternative routes",
    "IRCTC",
    "train booking",
    "waitlist",
    "route finder",
  ],
  openGraph: {
    title: "RailRoute AI — Smart Train Route Planner",
    description:
      "AI-powered alternative route discovery for Indian Railways. Find your way even when direct trains are sold out.",
    type: "website",
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={cn(
        "antialiased",
        spaceGrotesk.variable,
        plusJakarta.variable,
        "font-sans"
      )}
    >
      <body className="min-h-screen flex flex-col bg-background">
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
          <TooltipProvider>
            <Navbar />
            <main className="flex-1">{children}</main>
            <Footer />
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
