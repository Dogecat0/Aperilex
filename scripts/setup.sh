#!/bin/bash

# Aperilex Development Environment Setup Script
set -e

echo "Setting up Aperilex development environment..."

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
fi

# Set up Docker user IDs for proper file permissions
USER_ID=$(id -u)
GROUP_ID=$(id -g)

echo "Setting up Docker user configuration..."
echo "USER_ID: $USER_ID"
echo "GROUP_ID: $GROUP_ID"

# Add or update UID/GID in .env file
if grep -q "^UID=" .env; then
    sed -i "s/^UID=.*/UID=$USER_ID/" .env
else
    echo "UID=$USER_ID" >> .env
fi

if grep -q "^GID=" .env; then
    sed -i "s/^GID=.*/GID=$GROUP_ID/" .env
else
    echo "GID=$GROUP_ID" >> .env
fi

# Ensure data directory exists with proper permissions
echo "Setting up data directory..."
mkdir -p data/{filings,analyses,tasks,metadata}
chmod -R 755 data/

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Update your .env file with your API keys and email"
echo "2. Run: docker-compose up --build"
echo ""
echo "Database migrations will run automatically when containers start."
echo "Companies will be auto-populated from EDGAR when analyzing filings."
echo ""
echo "For a clean rebuild:"
echo "1. Run: docker-compose down -v"
echo "2. Run: docker-compose up --build"
echo ""
echo "To reset database with test data:"
echo "1. Run: ./scripts/reset_database.sh"
