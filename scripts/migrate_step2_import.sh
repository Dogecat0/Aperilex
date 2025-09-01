#!/bin/bash
# Step 2: Import from S3 to Aurora
# Run this script from ELASTIC BEANSTALK instance via SSM

set -e

echo "============================================"
echo "Aperilex AWS Migration - Step 2: IMPORT"
echo "============================================"
echo ""

# Check if running on Beanstalk
if [ ! -d "/var/app/current" ]; then
    echo "WARNING: Not running on Elastic Beanstalk instance"
    echo "This script should be run from the Beanstalk environment via SSM"
    echo ""
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Navigate to application directory
cd /var/app/current 2>/dev/null || cd .

# Get the S3 dump key
if [ -z "$1" ]; then
    echo "Finding latest dump in S3..."

    # List migrations and get the latest one
    LATEST_DUMP=$(aws s3 ls s3://${AWS_S3_BUCKET}/migrations/ --region ${AWS_REGION} 2>/dev/null | grep "aperilex_db_" | sort | tail -n 1 | awk '{print $4}')

    if [ -z "$LATEST_DUMP" ]; then
        echo "ERROR: No database dumps found in S3"
        echo "Please run Step 1 (export) first from your local machine"
        exit 1
    fi

    DUMP_KEY="migrations/$LATEST_DUMP"
    echo "Found dump: $DUMP_KEY"
    echo ""
    read -p "Use this dump? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Please specify dump key as argument:"
        echo "  $0 migrations/aperilex_db_TIMESTAMP.sql"
        exit 1
    fi
else
    DUMP_KEY="$1"
fi

# Run the import
echo ""
echo "Starting import from: $DUMP_KEY"
echo "Target database: ${DB_HOST}/${DB_NAME}"
echo ""

python scripts/migrate_to_aws_simplified.py --import --dump-key "$DUMP_KEY"

echo ""
echo "============================================"
echo "Migration Complete!"
echo "============================================"
echo ""
echo "Your data has been successfully migrated to AWS!"
echo ""
echo "Verification steps:"
echo "1. Check application logs:"
echo "   tail -f /var/log/eb-engine.log"
echo ""
echo "2. Test the application:"
echo "   curl http://localhost/"
echo ""
echo "3. Check CloudWatch logs in AWS Console"
echo ""
