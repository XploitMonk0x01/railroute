-- RailRoute AI — Full PostgreSQL Schema (Architecture v1.0)
-- Run this to migrate from the simplified schema to the complete one

-- Extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ─────────────────────────────────────────────
-- STATIONS
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS stations (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code            TEXT UNIQUE NOT NULL,              -- e.g. "ADI", "NDLS"
    name            TEXT NOT NULL,
    city            TEXT,
    state           TEXT,
    zone            TEXT,                              -- NR, WR, CR etc.
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,
    score           INTEGER NOT NULL DEFAULT 0,        -- computed rank
    is_junction     BOOLEAN NOT NULL DEFAULT FALSE,
    train_count     INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_stations_score  ON stations (score DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_stations_code_lower ON stations (LOWER(code));

-- ─────────────────────────────────────────────
-- TRAINS
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS trains (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    number          TEXT UNIQUE NOT NULL,              -- e.g. "12953"
    name            TEXT NOT NULL,
    train_type      TEXT,                              -- Rajdhani, Express, SF, Passenger
    origin_code     TEXT REFERENCES stations(code) ON DELETE SET NULL,
    destination_code TEXT REFERENCES stations(code) ON DELETE SET NULL,
    total_distance  INTEGER,                           -- km
    run_days        INTEGER[] NOT NULL DEFAULT '{}',   -- [0,1,2,3,4,5,6] (Mon-Sun)
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_trains_number ON trains (number);

-- ─────────────────────────────────────────────
-- TRAIN HALTS (every stop of every train)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS train_halts (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    train_id            BIGINT NOT NULL REFERENCES trains(id) ON DELETE CASCADE,
    station_code        TEXT NOT NULL REFERENCES stations(code) ON DELETE RESTRICT,
    halt_sequence       INTEGER NOT NULL,
    arrival_time        TIME,                          -- NULL for origin
    departure_time      TIME,                          -- NULL for terminus
    halt_duration       INTEGER,                       -- minutes
    distance_from_origin INTEGER,                     -- km
    day_count           SMALLINT NOT NULL DEFAULT 1,  -- which day of journey
    UNIQUE (train_id, halt_sequence)
);
CREATE INDEX IF NOT EXISTS idx_halts_station     ON train_halts (station_code);
CREATE INDEX IF NOT EXISTS idx_halts_train_seq   ON train_halts (train_id, halt_sequence);

-- ─────────────────────────────────────────────
-- TRAIN CLASSES
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS train_classes (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    train_id            BIGINT NOT NULL REFERENCES trains(id) ON DELETE CASCADE,
    class_code          TEXT NOT NULL,                 -- 1A, 2A, 3A, SL, CC, EC
    total_seats         INTEGER,
    base_fare_per_km    NUMERIC(5,3)
);
CREATE INDEX IF NOT EXISTS idx_train_classes_train ON train_classes (train_id);

-- ─────────────────────────────────────────────
-- TRAIN SEGMENTS (direct source→dest edges, used by graph engine)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS train_segments (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    train_number    TEXT NOT NULL REFERENCES trains(number) ON DELETE CASCADE,
    from_station    TEXT NOT NULL REFERENCES stations(code) ON DELETE RESTRICT,
    to_station      TEXT NOT NULL REFERENCES stations(code) ON DELETE RESTRICT,
    departure       TIME NOT NULL,
    arrival         TIME NOT NULL,
    duration_min    INTEGER NOT NULL,
    distance_km     INTEGER NOT NULL,
    fare            NUMERIC(10,2) NOT NULL,
    class_code      TEXT NOT NULL,
    available_seats INTEGER NOT NULL DEFAULT 0,
    run_days        INTEGER[] NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_train_segments_from   ON train_segments (from_station);
CREATE INDEX IF NOT EXISTS idx_train_segments_to     ON train_segments (to_station);
CREATE INDEX IF NOT EXISTS idx_train_segments_number ON train_segments (train_number);

-- ─────────────────────────────────────────────
-- SEAT AVAILABILITY (date-specific)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS seat_availability (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    train_id        BIGINT NOT NULL REFERENCES trains(id) ON DELETE CASCADE,
    journey_date    DATE NOT NULL,
    class_code      TEXT NOT NULL,
    from_station    TEXT NOT NULL,
    to_station      TEXT NOT NULL,
    available_seats INTEGER NOT NULL DEFAULT 0,
    wl_number       INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'AVAILABLE' CHECK (status IN ('AVAILABLE','WL','REGRET','RAC')),
    quota           TEXT NOT NULL DEFAULT 'GN',
    fare            NUMERIC(10,2),
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (train_id, journey_date, class_code, from_station, to_station, quota)
);
CREATE INDEX IF NOT EXISTS idx_avail_train_date   ON seat_availability (train_id, journey_date);
CREATE INDEX IF NOT EXISTS idx_avail_station_pair ON seat_availability (from_station, to_station);
CREATE INDEX IF NOT EXISTS idx_avail_date_status  ON seat_availability (journey_date, status);

-- ─────────────────────────────────────────────
-- USERS
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email           TEXT UNIQUE NOT NULL,
    phone           TEXT,
    password_hash   TEXT NOT NULL,
    display_name    TEXT,
    preferences     JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_lower ON users (LOWER(email));

-- ─────────────────────────────────────────────
-- ROUTE SEARCHES (user history)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS route_searches (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         BIGINT REFERENCES users(id) ON DELETE SET NULL,
    source_code     TEXT NOT NULL,
    destination_code TEXT NOT NULL,
    journey_date    DATE NOT NULL,
    result_snapshot JSONB,
    searched_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_route_searches_user ON route_searches (user_id);

-- ─────────────────────────────────────────────
-- WATCHLIST
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS watchlist (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         BIGINT REFERENCES users(id) ON DELETE CASCADE,
    source_code     TEXT NOT NULL,
    destination_code TEXT NOT NULL,
    journey_date    DATE NOT NULL,
    preferred_class TEXT,
    max_budget      NUMERIC(10,2),
    notify_on       TEXT[] NOT NULL DEFAULT '{}',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_watchlist_active ON watchlist (is_active, journey_date);
CREATE INDEX IF NOT EXISTS idx_watchlist_user   ON watchlist (user_id);

-- ─────────────────────────────────────────────
-- NOTIFICATIONS
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notifications (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         BIGINT REFERENCES users(id) ON DELETE CASCADE,
    watchlist_id    BIGINT REFERENCES watchlist(id) ON DELETE SET NULL,
    type            TEXT NOT NULL,
    message         TEXT NOT NULL,
    channel         TEXT NOT NULL DEFAULT 'EMAIL' CHECK (channel IN ('EMAIL','SMS','PUSH')),
    sent_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    read_at         TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications (user_id);
