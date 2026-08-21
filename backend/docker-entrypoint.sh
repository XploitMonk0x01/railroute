#!/bin/bash
set -e

echo "Running RailRoute Backend startup tasks..."

PORT="${PORT:-8000}"

# Seed database if DB connection is available
if [ -n "$RAILROUTE_DATABASE_URL" ]; then
    echo "Attempting database schema init and seed..."
    python seed_db.py || echo "Seeding completed or already present."
fi

echo "Starting FastAPI backend server on 0.0.0.0:${PORT}..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
