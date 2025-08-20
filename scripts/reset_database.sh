#!/bin/bash

# Database Reset Script for Aperilex
# This script cleans the PostgreSQL database, clears RabbitMQ queues, then runs migrations

set -e  # Exit on any error

echo "🗑️  Starting database reset..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker containers are running
echo "📋 Checking Docker containers..."
if ! docker ps | grep -q "aperilex-postgres-1"; then
    echo -e "${RED}❌ PostgreSQL container is not running. Please start with 'docker-compose up -d'${NC}"
    exit 1
fi

if ! docker ps | grep -q "aperilex-rabbitmq-1"; then
    echo -e "${RED}❌ RabbitMQ container is not running. Please start with 'docker-compose up -d'${NC}"
    exit 1
fi

if ! docker ps | grep -q "aperilex-app-1"; then
    echo -e "${RED}❌ App container is not running. Please start with 'docker-compose up -d'${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker containers are running${NC}"

# Step 1: Clean PostgreSQL Database
echo -e "\n${YELLOW}🧹 Cleaning PostgreSQL database...${NC}"
docker exec aperilex-postgres-1 psql -U aperilex -d aperilex -c \
    "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO aperilex; GRANT ALL ON SCHEMA public TO public;"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ PostgreSQL database cleaned successfully${NC}"
else
    echo -e "${RED}❌ Failed to clean PostgreSQL database${NC}"
    exit 1
fi

# Step 2: Clear RabbitMQ Queues
echo -e "\n${YELLOW}🧹 Clearing RabbitMQ queues...${NC}"
docker exec aperilex-rabbitmq-1 rabbitmqctl purge_queue analysis_queue || echo "Queue analysis_queue not found (ok)"
docker exec aperilex-rabbitmq-1 rabbitmqctl purge_queue validation_queue || echo "Queue validation_queue not found (ok)"

echo -e "${GREEN}✅ RabbitMQ queues cleared${NC}"

# Step 3: Clear local storage data
echo -e "\n${YELLOW}🧹 Clearing local storage data...${NC}"
rm -rf data/filings/* data/analyses/* data/tasks/* data/metadata/* 2>/dev/null || true
mkdir -p data/{filings,analyses,tasks,metadata}

echo -e "${GREEN}✅ Local storage data cleared${NC}"

# Step 4: Run Alembic Migrations inside Docker container
echo -e "\n${YELLOW}🔄 Running Alembic migrations...${NC}"
docker exec aperilex-app-1 alembic upgrade head

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Migrations completed successfully${NC}"
else
    echo -e "${RED}❌ Migrations failed${NC}"
    exit 1
fi

echo -e "\n${GREEN}🎉 Database reset completed successfully!${NC}"
echo "📋 Summary:"
echo "   - PostgreSQL database: cleaned and migrated"
echo "   - RabbitMQ queues: cleared"
echo "   - Local storage: cleared"
echo ""
echo "💡 Your database is now ready for fresh data."
echo "🔄 Companies will be auto-populated from EDGAR when first filing is analyzed."

# Optional: Seed with test data (uncomment if needed)
echo "Seeding test data..."
docker exec aperilex-app-1 python scripts/import_filings.py --tickers AAPL --filing-types 10-K,10-Q --limit 5
