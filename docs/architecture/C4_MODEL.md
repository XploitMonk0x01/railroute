# RailRoute Architecture (C4 Model)

This document describes the software architecture of RailRoute using the C4 model for visualizing software architecture.

## Level 1: System Context Diagram

The System Context diagram provides a high-level view of RailRoute and its interactions with users and external systems.

```mermaid
C4Context
    title System Context diagram for RailRoute

    Person(user, "Traveler", "A user of RailRoute searching for train availability and optimal routes.")
    
    System(railroute, "RailRoute System", "Provides train route optimization and live availability tracking.")
    
    System_Ext(irctc, "IRCTC / ConfirmTKT", "External train booking and availability systems.")

    Rel(user, railroute, "Searches for routes, checks availability")
    Rel(railroute, irctc, "Scrapes live availability data using headless browsers", "HTTPS/Playwright")
```

## Level 2: Container Diagram

The Container diagram zooms into the RailRoute System to show the high-level technical containers that make up the system.

```mermaid
C4Container
    title Container diagram for RailRoute

    Person(user, "Traveler", "A user of RailRoute searching for train availability and optimal routes.")

    System_Boundary(c1, "RailRoute System") {
        Container(spa, "Single Page Application", "Next.js, React, Tailwind CSS", "Provides the user interface for route searching and availability visualization.")
        
        Container(api, "API Application", "Python, FastAPI", "Handles business logic, route computation (NetworkX), and API orchestration.")
        
        Container(scraper, "Availability Scraper", "Python, Playwright", "Background worker process that automates Chromium to scrape live IRCTC/ConfirmTKT data.")
        
        ContainerDb(db, "Database", "PostgreSQL", "Stores user accounts, static station/train data, and cached availability results.")
    }
    
    System_Ext(irctc, "IRCTC / ConfirmTKT", "External train booking and availability systems.")

    Rel(user, spa, "Visits railroute.com", "HTTPS")
    Rel(spa, api, "Makes API calls", "JSON/HTTPS")
    Rel(api, scraper, "Delegates scraping tasks", "Internal ThreadPool")
    Rel(api, db, "Reads and writes data", "SQL/TCP")
    Rel(scraper, irctc, "Scrapes HTML data", "HTTPS")
```

## Component Architecture (Backend)

The FastAPI backend follows Clean Architecture and Domain-Driven Design principles:

- **Routes (`app/api/v1/routes`)**: Handles HTTP requests, input validation, and HTTP responses.
- **Services (`app/services`)**: Contains the core business logic (e.g., `RouteService` building queries, `StationService`).
- **Repositories (`app/repositories`)**: Abstracts data access. Uses Dependency Inversion to allow swapping out implementations (e.g., `PgRailRepository`).
- **Core (`app/core`)**: Cross-cutting concerns, configuration, and singletons (like the in-memory `NetworkX` graph).
- **Scraper (`automation/scraper`)**: A strictly decoupled module responsible purely for data acquisition via Playwright.

## Architectural Decisions

> [!NOTE]
> **Scraper Decoupling**: The scraper uses Playwright but executes in a `ThreadPoolExecutor` using a dedicated `ProactorEventLoop`. This prevents C-extension crashes from halting the Uvicorn asyncio loop while remaining performant.

> [!NOTE]
> **Graph Routing**: Routing computation is performed entirely in memory using `NetworkX` initialized on application startup. This avoids heavy, recursive SQL queries and significantly speeds up pathfinding.
