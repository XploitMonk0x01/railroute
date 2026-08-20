#!/bin/bash
set -e

echo "Running RailRoute Backend startup tasks..."

# Seed database if DB connection is available
if [ -n "$RAILROUTE_DATABASE_URL" ]; then
    echo "Attempting database seed..."
    python seed_db.py || echo "Seeding skipped or failed (may already be seeded)."
fi

echo "Starting FastAPI backend server on 0.0.0.0:8000..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
