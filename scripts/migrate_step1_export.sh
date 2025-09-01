#!/bin/bash
# Step 1: Export local data and upload to AWS S3
# Run this script from your LOCAL development machine

set -e

echo "============================================"
echo "Aperilex AWS Migration - Step 1: EXPORT"
echo "============================================"
echo "This script will:"
echo "1. Export your local PostgreSQL database"
echo "2. Upload the dump to S3"
echo "3. Sync local files to S3"
echo ""

# Check if running in Docker environment
if [ ! -f /.dockerenv ] && [ ! "$(docker ps -q -f name=aperilex-postgres-1)" ]; then
    echo "ERROR: PostgreSQL container 'aperilex-postgres-1' not running"
    echo "Please start your local development environment first:"
    echo "  docker-compose up -d"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "ERROR: AWS credentials not configured"
    echo "Please run: aws configure"
    exit 1
fi

# Set Aurora password for later verification
read -p "Enter Aurora database password (will be set as AURORA_PASSWORD): " -s aurora_pass
echo
export AURORA_PASSWORD="$aurora_pass"

# Run the migration export
echo ""
echo "Starting export..."
python scripts/migrate_to_aws_simplified.py --export

echo ""
echo "============================================"
echo "Step 1 Complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "1. Enable SSM on your Beanstalk instance (if not already done):"
echo "   aws iam attach-role-policy \\"
echo "     --role-name eb-instance-role-5bfbef9 \\"
echo "     --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore \\"
echo "     --region us-east-2"
echo ""
echo "2. Wait 5-10 minutes for SSM to activate"
echo ""
echo "3. Connect to your Beanstalk instance:"
echo "   aws ssm start-session --target i-083b20fbd26a450e9 --region us-east-2"
echo ""
echo "4. Run Step 2 import script (copy the command from above output)"
echo ""
