#!/bin/bash

# AWS-specific entrypoint script that fetches database password from Secrets Manager
# and constructs the DATABASE_URL before calling the main entrypoint

set -e

echo "🔧 AWS Entrypoint: Configuring environment..."

# Check if we're in AWS environment
if [ -n "$DB_PASSWORD_SECRET_ARN" ]; then
    echo "📥 Fetching database password from AWS Secrets Manager..."

    # Fetch the secret value
    SECRET_JSON=$(aws secretsmanager get-secret-value --secret-id "$DB_PASSWORD_SECRET_ARN" --query SecretString --output text --region "${AWS_REGION:-us-east-2}")

    # Extract password from JSON
    DB_PASSWORD=$(echo "$SECRET_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin)['password'])")

    # Construct DATABASE_URL
    if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ] && [ -n "$DB_USER" ] && [ -n "$DB_NAME" ]; then
        export DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
        echo "✅ DATABASE_URL configured from AWS components"
    else
        echo "❌ Error: Missing database configuration variables"
        echo "DB_HOST=$DB_HOST"
        echo "DB_PORT=$DB_PORT"
        echo "DB_USER=$DB_USER"
        echo "DB_NAME=$DB_NAME"
        exit 1
    fi

    # Set ENVIRONMENT to production if not already set
    export ENVIRONMENT="${ENVIRONMENT:-production}"

    # Set other AWS-specific environment variables
    export QUEUE_SERVICE_TYPE="${QUEUE_SERVICE_TYPE:-sqs}"
    export STORAGE_SERVICE_TYPE="${STORAGE_SERVICE_TYPE:-s3}"
    export WORKER_SERVICE_TYPE="${WORKER_SERVICE_TYPE:-lambda}"
else
    echo "ℹ️  Not in AWS environment (DB_PASSWORD_SECRET_ARN not set), using existing DATABASE_URL"
fi

# Call the main entrypoint
echo "🚀 Starting main application..."
exec /app/scripts/docker-entrypoint.sh "$@"
