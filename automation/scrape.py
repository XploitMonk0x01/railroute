#!/usr/bin/env python3
"""
automation/scrape.py
─────────────────────
CLI entrypoint for the RailRoute IRCTC availability scraper.

Usage examples
──────────────
# Single route, explicit credentials
python scrape.py --from HWH --to PNBE --date 2026-07-20 --class 3A

# Headless (server / CI mode)
python scrape.py --from HWH --to PNBE --date 2026-07-20 --class 3A --headless

# Scrape all active watchlist entries from the DB at once
python scrape.py --watchlist

# Override the DB URL
python scrape.py --from HWH --to PNBE --date 2026-07-20 \\
    --db-url postgresql://user:pass@host/railroute

# Multiple routes in one run (repeat --from/--to/--date for each)
python scrape.py \\
    --route "HWH,PNBE,2026-07-20,3A" \\
    --route "HWH,ASN,2026-07-20,SL"
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import date, datetime

import psycopg
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

# ── local imports (works when run from the automation/ directory) ──
sys.path.insert(0, os.path.dirname(__file__))
from scraper import IRCTCClient, RouteQuery
from db import upsert_results

# ──────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────

load_dotenv()  # read .env if present

logging.basicConfig(
    level    = logging.INFO,
    format   = "%(message)s",
    datefmt  = "[%X]",
    handlers = [RichHandler(rich_tracebacks=True)],
)
log     = logging.getLogger("scrape")
console = Console()


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _parse_date(s: str) -> date:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(
        f"Invalid date: '{s}'. Use YYYY-MM-DD, DD/MM/YYYY, or DD-MM-YYYY."
    )


def _parse_route_arg(s: str) -> RouteQuery:
    """Parse '--route FROM,TO,DATE,CLASS[,QUOTA]' shorthand."""
    parts = [p.strip() for p in s.split(",")]
    if len(parts) < 4:
        raise argparse.ArgumentTypeError(
            f"--route must be 'FROM,TO,DATE,CLASS[,QUOTA]', got: {s!r}"
        )
    return RouteQuery(
        from_code  = parts[0],
        to_code    = parts[1],
        date       = _parse_date(parts[2]),
        class_code = parts[3],
        quota      = parts[4] if len(parts) > 4 else "GN",
    )


def _load_watchlist_queries(db_url: str) -> list[RouteQuery]:
    """Read all active watchlist rows from the DB and build RouteQuery objects."""
    queries: list[RouteQuery] = []
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT source_code, destination_code, journey_date, preferred_class
                FROM   watchlist
                WHERE  is_active = TRUE
                  AND  journey_date >= CURRENT_DATE
                ORDER  BY journey_date
            """)
            for row in cur.fetchall():
                src, dst, jdate, cls = row
                queries.append(RouteQuery(
                    from_code  = src,
                    to_code    = dst,
                    date       = jdate,
                    class_code = cls or "3A",
                ))
    log.info("Loaded %d active watchlist queries from DB.", len(queries))
    return queries


def _print_results_table(results: list) -> None:
    table = Table(title="Scraped Availability", show_lines=True)
    table.add_column("Train",   style="cyan",  no_wrap=True)
    table.add_column("Name",    style="white")
    table.add_column("Route",   style="yellow")
    table.add_column("Date",    style="blue")
    table.add_column("Class",   style="magenta")
    table.add_column("Status",  style="green")
    table.add_column("Seats",   style="white")
    table.add_column("Fare ₹",  style="white")

    for r in results:
        seat_str   = str(r.available_seats) if r.status == "AVAILABLE" else f"WL#{r.wl_number}" if r.status == "WL" else "-"
        status_fmt = f"[green]{r.status}[/green]" if r.status == "AVAILABLE" else f"[yellow]{r.status}[/yellow]" if r.status in ("WL", "RAC") else f"[red]{r.status}[/red]"
        table.add_row(
            r.train_number,
            r.train_name[:30],
            f"{r.from_code}→{r.to_code}",
            r.journey_date.isoformat(),
            r.class_code,
            status_fmt,
            seat_str,
            f"{r.fare:.0f}" if r.fare else "?",
        )
    console.print(table)


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

async def _run(args: argparse.Namespace) -> int:
    """Async entry point — returns exit code."""

    db_url   = args.db_url or os.getenv("RAILROUTE_DATABASE_URL", "postgresql://master@127.0.0.1:5432/railroute")
    irctc_user = args.user or os.getenv("IRCTC_USER", "")
    irctc_pass = args.password or os.getenv("IRCTC_PASS", "")
    headless  = args.headless or os.getenv("SCRAPER_HEADLESS", "false").lower() == "true"
    max_tabs  = int(os.getenv("SCRAPER_MAX_TABS", "6"))

    # ── build list of queries ──────────────────────────────
    queries: list[RouteQuery] = []

    if args.watchlist:
        queries = _load_watchlist_queries(db_url)
        if not queries:
            log.warning("No active watchlist entries found. Nothing to scrape.")
            return 0
    elif args.route:
        queries = list(args.route)   # already parsed by _parse_route_arg
    elif args.from_station and args.to_station and args.date:
        queries = [
            RouteQuery(
                from_code  = args.from_station,
                to_code    = args.to_station,
                date       = args.date,
                class_code = args.travel_class,
                quota      = args.quota,
            )
        ]
    else:
        log.error("Provide --from/--to/--date, --route, or --watchlist.")
        return 1

    log.info("Queries to run: %d", len(queries))

    # ── scrape ──────────────────────────────────────────────
    async with IRCTCClient(headless=headless, max_tabs=max_tabs) as client:
        if irctc_user and irctc_pass:
            await client.login(irctc_user, irctc_pass)
        else:
            log.warning(
                "No IRCTC credentials provided. "
                "Set IRCTC_USER / IRCTC_PASS or use --user / --password. "
                "Login-gated data may not be accessible."
            )

        results = await client.multi_tab_search(queries)

    if not results:
        log.warning("No availability data was returned.")
        return 0

    # ── display ──────────────────────────────────────────────
    _print_results_table(results)

    # ── write to DB ──────────────────────────────────────────
    if not args.dry_run:
        log.info("Writing %d results to database …", len(results))
        with psycopg.connect(db_url) as conn:
            ok, skipped = upsert_results(conn, results)
        console.print(
            f"[bold green]✓ DB write:[/bold green] "
            f"{ok} upserted, {skipped} skipped (train not in DB)."
        )
    else:
        log.info("[DRY RUN] Skipping DB write.")

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog        = "scrape.py",
        description = "RailRoute IRCTC availability scraper (Pure Playwright)",
        formatter_class = argparse.ArgumentDefaultsHelpFormatter,
    )

    # ── target options (mutually exclusive groups) ──────────
    target = parser.add_argument_group("Target (pick one)")
    target.add_argument("--from",    dest="from_station", metavar="CODE",  help="Source station code, e.g. HWH")
    target.add_argument("--to",      dest="to_station",   metavar="CODE",  help="Destination station code, e.g. PNBE")
    target.add_argument("--date",    dest="date",         metavar="DATE",  type=_parse_date, help="Journey date (YYYY-MM-DD or DD/MM/YYYY)")
    target.add_argument("--class",   dest="travel_class", metavar="CLASS", default="3A",  help="Travel class: 1A|2A|3A|SL|CC|EC")
    target.add_argument("--quota",   dest="quota",        metavar="QUOTA", default="GN",  help="Quota: GN|TQ|PT|LD|SS")
    target.add_argument("--route",   dest="route",        metavar="CSV",   type=_parse_route_arg, action="append",
                        help="Shorthand: FROM,TO,DATE,CLASS[,QUOTA] — repeat for multiple routes")
    target.add_argument("--watchlist", action="store_true",
                        help="Scrape all active watchlist entries from the DB")

    # ── credentials ─────────────────────────────────────────
    creds = parser.add_argument_group("IRCTC Credentials")
    creds.add_argument("--user",     metavar="USERNAME", help="IRCTC username (or set IRCTC_USER env)")
    creds.add_argument("--password", metavar="PASSWORD", help="IRCTC password (or set IRCTC_PASS env)")

    # ── behaviour ────────────────────────────────────────────
    beh = parser.add_argument_group("Behaviour")
    beh.add_argument("--db-url",  metavar="URL",    help="PostgreSQL connection string (or set RAILROUTE_DATABASE_URL)")
    beh.add_argument("--headless", action="store_true", help="Run Chrome in headless mode")
    beh.add_argument("--dry-run",  action="store_true", help="Scrape but do NOT write to the DB")
    beh.add_argument("--verbose",  action="store_true", help="Enable DEBUG logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    exit_code = asyncio.run(_run(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
