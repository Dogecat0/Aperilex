#!/bin/bash

# Docker entrypoint script for Aperilex
# Handles database migrations and service startup

set -e

echo "🚀 Starting Aperilex..."

# Function to wait for database
wait_for_db() {
    echo "⏳ Waiting for database to be ready..."

    while ! python -c "
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from src.shared.config.settings import Settings

async def check_db():
    try:
        settings = Settings()
        engine = create_async_engine(settings.database_url)
        async with engine.connect() as conn:
            await conn.execute(text('SELECT 1'))
        await engine.dispose()
        return True
    except Exception as e:
        print(f'Database not ready: {e}')
        return False

result = asyncio.run(check_db())
sys.exit(0 if result else 1)
"; do
        echo "⏳ Database not ready yet, waiting 2 seconds..."
        sleep 2
    done

    echo "✅ Database is ready!"
}

# Function to run migrations
run_migrations() {
    echo "🔄 Running database migrations..."

    if alembic upgrade head; then
        echo "✅ Migrations completed successfully!"
    else
        echo "❌ Migrations failed!"
        exit 1
    fi
}

# Main logic
if [ "$1" = "app" ]; then
    echo "🌐 Starting web application..."
    wait_for_db
    run_migrations
    exec uvicorn src.presentation.api.app:app --host 0.0.0.0 --port 8000 --reload

elif [ "$1" = "worker" ]; then
    echo "⚙️  Starting background worker..."
    wait_for_db
    # Workers don't need to run migrations, app service handles it
    exec python scripts/run_worker.py --log-level INFO

elif [ "$1" = "migrate" ]; then
    echo "🔄 Running migrations only..."
    wait_for_db
    run_migrations

else
    echo "🔧 Running custom command: $@"
    exec "$@"
fi
