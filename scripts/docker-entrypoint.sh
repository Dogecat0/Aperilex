#!/bin/bash

# Docker entrypoint script for Aperilex
# Handles database migrations and service startup

set -e

echo "🚀 Starting Aperilex..."

ensure_pythonpath() {
    local app_path="/app"
    case ":${PYTHONPATH:-}:" in
        *":${app_path}:"*) ;;
        *) export PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}${app_path}" ;;
    esac
}

load_runtime_secrets() {
    local secrets_dir="${DOCKER_SECRETS_DIR:-/run/secrets}"
    if [ ! -d "$secrets_dir" ]; then
        echo "❌ Secrets directory not found: $secrets_dir"
        exit 1
    fi

    local postgres_secret_name="${POSTGRES_PASSWORD_SECRET_NAME:-postgres_password}"
    local postgres_secret_path="$secrets_dir/$postgres_secret_name"

    if [ ! -f "$postgres_secret_path" ]; then
        echo "❌ Required secret missing: $postgres_secret_path"
        exit 1
    fi

    local postgres_password
    postgres_password="$(tr -d '\r\n' < "$postgres_secret_path")"
    if [ -z "$postgres_password" ]; then
        echo "❌ Postgres password secret '$postgres_secret_name' is empty"
        exit 1
    fi

    export DATABASE_URL="postgresql+asyncpg://aperilex:${postgres_password}@postgres/aperilex"
    export APERILEX_DATABASE_PASSWORD_SECRET="$postgres_secret_name"

    for secret_var in GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET OPENAI_API_KEY GOOGLE_API_KEY; do
        local secret_name_var="${secret_var}_SECRET_NAME"
        local secret_name="${!secret_name_var:-$secret_var}"
        local secret_path="$secrets_dir/$secret_name"
        if [ -f "$secret_path" ]; then
            export "$secret_var"="$(tr -d '\r\n' < "$secret_path")"
        fi
    done

    for key_var in JWT_PRIVATE_KEY JWT_PUBLIC_KEY; do
        local key_name_var="${key_var}_SECRET_NAME"
        local key_name="${!key_name_var:-$key_var}"
        local key_path="$secrets_dir/$key_name"
        if [ -f "$key_path" ]; then
            export "${key_var}_PATH"="$key_path"
        fi
    done

    echo "🔐 Secrets loaded from $secrets_dir"
}

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

is_truthy() {
    local value="${1:-}"
    value="$(echo "$value" | tr '[:upper:]' '[:lower:]')"

    case "$value" in
        true | 1 | yes | y) return 0 ;;
        *) return 1 ;;
    esac
}

# Main logic
ensure_pythonpath
load_runtime_secrets
if [ "$1" = "app" ]; then
    echo "🌐 Starting web application..."
    wait_for_db
    if is_truthy "${RUN_MIGRATIONS_ON_STARTUP:-true}"; then
        run_migrations
    else
        echo "⏭️  Skipping migrations on startup (RUN_MIGRATIONS_ON_STARTUP=${RUN_MIGRATIONS_ON_STARTUP})"
    fi

    UVICORN_COMMAND=(
        uvicorn
        src.presentation.api.app:app
        --host 0.0.0.0
        --port 8000
    )

    if is_truthy "${UVICORN_RELOAD:-true}"; then
        UVICORN_COMMAND+=(--reload)
    fi

    if [ -n "${UVICORN_WORKERS:-}" ]; then
        UVICORN_COMMAND+=(--workers "${UVICORN_WORKERS}")
    fi

    exec "${UVICORN_COMMAND[@]}"

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
