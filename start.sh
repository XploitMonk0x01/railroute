#!/usr/bin/env bash
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================================${NC}"
echo -e "${GREEN}         RailRoute AI — Full Stack Setup & Launcher        ${NC}"
echo -e "${BLUE}============================================================${NC}"

# Step 1: Check Docker installation
echo -e "\n${YELLOW}[1/4] Checking prerequisites...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed or not in PATH.${NC}"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose v2 is not available.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker & Docker Compose detected.${NC}"

# Step 2: Ensure environment files exist
echo -e "\n${YELLOW}[2/4] Initializing environment configuration...${NC}"
if [ ! -f "backend/.env" ]; then
    echo "Creating backend/.env from .env.example..."
    cp backend/.env.example backend/.env
fi
echo -e "${GREEN}✓ Environment configuration ready.${NC}"

# Step 3: Launch Docker containers
echo -e "\n${YELLOW}[3/4] Building and firing up Docker containers...${NC}"
echo "  - Creating PostgreSQL database 'railroute'"
echo "  - Loading schema from backend/schema.sql"
echo "  - Seeding static route topology (stations, trains, segments via seed_db.py)"
echo "  - Building FastAPI backend & Next.js frontend"
echo ""

docker compose up --build -d

# Step 4: Health Check & Verification
echo -e "\n${YELLOW}[4/4] Waiting for services to initialize...${NC}"
attempt=0
max_attempts=30

echo "Waiting for Backend API (http://localhost:8000/docs)..."
until curl -s http://localhost:8000/docs > /dev/null || [ $attempt -eq $max_attempts ]; do
    attempt=$((attempt+1))
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}Warning: Backend startup timed out. Check container logs with 'docker compose logs backend'${NC}"
else
    echo -e "${GREEN}✓ Backend API is ready!${NC}"
fi

echo -e "\n${BLUE}============================================================${NC}"
echo -e "${GREEN} 🎉 RailRoute AI Full Stack is UP and RUNNING!${NC}"
echo -e "${BLUE}============================================================${NC}"
echo -e "  🌐 Frontend App:     ${GREEN}http://localhost:3000${NC}"
echo -e "  ⚙️  Backend API Docs: ${GREEN}http://localhost:8000/docs${NC}"
echo -e "  🗄️  PostgreSQL DB:    ${GREEN}localhost:5432 (user: master, db: railroute)${NC}"
echo -e "${BLUE}============================================================${NC}"
echo -e "\nUseful Management Commands:"
echo -e "  View logs:          ${YELLOW}docker compose logs -f${NC}"
echo -e "  Stop stack:         ${YELLOW}docker compose down${NC}"
echo -e "  Re-seed database:   ${YELLOW}docker compose exec backend python seed_db.py${NC}"
echo -e "${BLUE}============================================================${NC}"
