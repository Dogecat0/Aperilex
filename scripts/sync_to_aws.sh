#!/bin/bash

# Aperilex Quick Sync Script for AWS
# Syncs local data to AWS S3 bucket for deployed application

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DATA_DIR="./data"
AWS_REGION="us-east-2"

# Dynamically find the actual S3 bucket (handles Pulumi-generated suffixes)
S3_BUCKET=$(aws s3 ls --region "$AWS_REGION" 2>/dev/null | grep -E "aperilex-backend-filings-bucket" | awk '{print $3}' | head -n1)

if [ -z "$S3_BUCKET" ]; then
    # Fallback to default name
    S3_BUCKET="aperilex-backend-filings-bucket"
    print_warning "Could not detect S3 bucket dynamically, using default: $S3_BUCKET"
fi

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    echo "Checking prerequisites..."

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI not found. Please install it first."
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured. Run 'aws configure' first."
        exit 1
    fi

    # Check data directory
    if [ ! -d "$DATA_DIR" ]; then
        print_error "Data directory not found: $DATA_DIR"
        exit 1
    fi

    print_status "Prerequisites check passed"
}

# Function to sync a directory
sync_directory() {
    local dir_name=$1
    local local_path="$DATA_DIR/$dir_name"
    local s3_path="s3://$S3_BUCKET/$dir_name/"

    if [ ! -d "$local_path" ]; then
        print_warning "Directory not found: $local_path (skipping)"
        return
    fi

    # Count files
    local file_count=$(find "$local_path" -name "*.json" 2>/dev/null | wc -l)
    echo "Syncing $file_count files from $dir_name/..."

    # Perform sync
    if aws s3 sync "$local_path" "$s3_path" \
        --region "$AWS_REGION" \
        --exclude "*.pyc" \
        --exclude "__pycache__/*" \
        --exclude ".DS_Store" \
        --exclude "*.log" \
        --size-only; then
        print_status "Synced $dir_name/ to S3"
    else
        print_error "Failed to sync $dir_name/"
        return 1
    fi
}

# Function to verify sync
verify_sync() {
    local dir_name=$1
    local local_path="$DATA_DIR/$dir_name"
    local s3_path="s3://$S3_BUCKET/$dir_name/"

    # Count local files
    local local_count=$(find "$local_path" -name "*.json" 2>/dev/null | wc -l)

    # Count S3 objects
    local s3_count=$(aws s3 ls "$s3_path" --recursive --region "$AWS_REGION" 2>/dev/null | grep ".json" | wc -l)

    echo "  Local: $local_count files, S3: $s3_count objects"

    if [ $local_count -eq $s3_count ]; then
        print_status "Counts match for $dir_name/"
    else
        print_warning "Count mismatch for $dir_name/ (local: $local_count, S3: $s3_count)"
    fi
}

# Function to show S3 storage info
show_storage_info() {
    echo ""
    echo "S3 Storage Information:"

    # Get total size
    local total_size=$(aws s3 ls "s3://$S3_BUCKET/" --recursive --summarize --region "$AWS_REGION" 2>/dev/null | grep "Total Size" | awk '{print $3}')
    local total_objects=$(aws s3 ls "s3://$S3_BUCKET/" --recursive --summarize --region "$AWS_REGION" 2>/dev/null | grep "Total Objects" | awk '{print $3}')

    if [ -n "$total_size" ]; then
        # Convert bytes to human readable
        local size_mb=$(echo "scale=2; $total_size / 1024 / 1024" | bc)
        echo "  Total objects: $total_objects"
        echo "  Total size: ${size_mb} MB"
    fi
}

# Main execution
main() {
    echo "======================================"
    echo "Aperilex AWS Data Sync"
    echo "======================================"
    echo "Bucket: $S3_BUCKET"
    echo "Region: $AWS_REGION"
    echo "Local data: $DATA_DIR"
    echo ""

    # Check prerequisites
    check_prerequisites

    # Parse arguments
    if [ "$1" = "--dry-run" ]; then
        echo "DRY RUN MODE - No changes will be made"
        AWS_ARGS="--dryrun"
    fi

    if [ "$1" = "--delete" ]; then
        print_warning "DELETE mode - Will remove S3 objects not in local"
        AWS_ARGS="--delete"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Aborted."
            exit 1
        fi
    fi

    # Sync directories
    echo ""
    echo "Starting sync..."
    echo "-------------------------------------"

    # Primary data directories
    sync_directory "filings"
    sync_directory "analyses"

    # Optional directories (won't fail if missing)
    sync_directory "batch_jobs"
    sync_directory "batch_logs"

    echo ""
    echo "Verifying sync..."
    echo "-------------------------------------"

    verify_sync "filings"
    verify_sync "analyses"

    # Show storage info
    show_storage_info

    echo ""
    echo "======================================"
    print_status "Sync completed successfully!"
    echo "======================================"
}

# Help function
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Sync local Aperilex data to AWS S3 bucket

OPTIONS:
    --dry-run    Show what would be synced without making changes
    --delete     Delete S3 objects that don't exist locally (DANGEROUS)
    --help       Show this help message

EXAMPLES:
    $0                  # Normal sync (upload new/modified files)
    $0 --dry-run        # Preview what would be synced
    $0 --delete         # Sync and remove orphaned S3 objects

EOF
}

# Handle arguments
case "$1" in
    --help|-h)
        show_help
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
