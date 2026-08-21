#!/usr/bin/env bash
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================================${NC}"
echo -e "${GREEN}    RailRoute AI — Dev Mode (Docker DB + Host App)        ${NC}"
echo -e "${BLUE}============================================================${NC}"

# Step 1: Start PostgreSQL container only
echo -e "\n${YELLOW}[1/3] Starting PostgreSQL container (railroute_db)...${NC}"
docker compose up -d db

# Step 2: Wait for DB and seed if needed
echo -e "\n${YELLOW}[2/3] Verifying database connection...${NC}"
attempt=0
max_attempts=15
until docker compose exec -T db pg_isready -U master -d railroute > /dev/null 2>&1 || [ $attempt -eq $max_attempts ]; do
    attempt=$((attempt+1))
    sleep 1
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}Error: PostgreSQL container failed to start.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ PostgreSQL container is healthy on localhost:5432.${NC}"

# Seed route topology into local database if needed
if [ -d "backend/.venv" ]; then
    echo "Running database seeder via local python virtualenv..."
    RAILROUTE_DATABASE_URL="postgresql://master:railroute_pass@127.0.0.1:5432/railroute" backend/.venv/bin/python backend/seed_db.py || true
fi

echo -e "\n${YELLOW}[3/3] Ready for local development!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo "To run the Backend on your system:"
echo "  cd backend && source .venv/bin/activate"
echo "  uvicorn app.main:app --reload --port 8000"
echo ""
echo "To run the Frontend on your system:"
echo "  cd frontend"
echo "  npm run dev"
echo -e "${GREEN}============================================================${NC}"
