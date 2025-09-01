# AWS Data Migration Summary

## Migration Strategy Overview

Based on your architecture analysis, here's the comprehensive migration plan for syncing your local containerized data to AWS:

## ✅ Key Findings

### Local Architecture
- **Database**: PostgreSQL in Docker (`aperilex-postgres-1`)
- **Storage**: Hierarchical file structure under `./data/`
  - `filings/{cik}/{accession}.json` - SEC filing documents
  - `analyses/{cik}/{filing_id}/{id}.json` - Analysis results
- **Data Volume**: ~400+ companies with filings and analyses

### AWS Architecture
- **Database**: Aurora Serverless v2 PostgreSQL (`aperilex-db-cluster`)
- **Storage**: S3 bucket (`aperilex-backend-filings-bucket`)
- **Region**: us-east-2
- **Storage Pattern**: Maintains same hierarchical structure as local

## 🚀 Migration Approach

### Option 1: Automated Migration Script (Recommended)
```bash
# Full migration with verification
python scripts/migrate_to_aws.py

# Test run first
python scripts/migrate_to_aws.py --dry-run
```

**Features:**
- Automatic AWS resource discovery
- Database backup before migration
- Progress tracking and verification
- Rollback capability

### Option 2: Manual Step-by-Step

#### Database Migration:
```bash
# 1. Export local database
docker exec aperilex-postgres-1 pg_dump -U aperilex -d aperilex \
  --no-owner --no-acl --clean --if-exists > aperilex_export.sql

# 2. Import to Aurora (requires Aurora endpoint and credentials)
psql -h <aurora-endpoint> -U db_admin -d aperilexdb -f aperilex_export.sql
```

#### File Storage Sync:
```bash
# Use the quick sync script
./scripts/sync_to_aws.sh

# Or manual AWS CLI
aws s3 sync ./data/filings/ s3://aperilex-backend-filings-bucket/filings/
aws s3 sync ./data/analyses/ s3://aperilex-backend-filings-bucket/analyses/
```

## 📊 Storage Layout Consistency

The migration maintains identical structure between local and S3:

```
Local:                              S3:
data/                              s3://aperilex-backend-filings-bucket/
├── filings/                       ├── filings/
│   └── {cik}/                    │   └── {cik}/
│       └── {accession}.json      │       └── {accession}.json
└── analyses/                      └── analyses/
    └── {cik}/                         └── {cik}/
        └── {filing_id}/                   └── {filing_id}/
            └── {id}.json                      └── {id}.json
```

This ensures the application's `S3StorageService` and `LocalFileStorageService` work identically.

## ⚡ Quick Commands

### For Regular Syncing:
```bash
# Quick sync (new/modified files only)
./scripts/sync_to_aws.sh

# Preview what will be synced
./scripts/sync_to_aws.sh --dry-run

# Full sync with cleanup
./scripts/sync_to_aws.sh --delete
```

### For Initial Migration:
```bash
# Complete migration with all checks
python scripts/migrate_to_aws.py

# Skip database if already migrated
python scripts/migrate_to_aws.py --skip-database

# Skip files if only need database
python scripts/migrate_to_aws.py --skip-files
```

## 🔍 Verification Steps

1. **Check S3 Upload:**
   ```bash
   aws s3 ls s3://aperilex-backend-filings-bucket/ --recursive | wc -l
   ```

2. **Verify Database:**
   ```sql
   -- Connect to Aurora and check counts
   SELECT 'companies' as table, COUNT(*) FROM companies
   UNION ALL
   SELECT 'filings', COUNT(*) FROM filings
   UNION ALL
   SELECT 'analyses', COUNT(*) FROM analyses;
   ```

3. **Test Application:**
   ```bash
   curl https://api.aperilexlabs.com/health
   curl https://api.aperilexlabs.com/api/v1/filings/<filing-id>
   ```

## ⚠️ Important Notes

1. **AWS Credentials Required**: Ensure AWS CLI is configured with proper credentials
2. **Database Password**: Retrieved automatically from AWS Secrets Manager
3. **Large Datasets**: For very large datasets, consider using AWS Database Migration Service (DMS)
4. **Incremental Updates**: After initial migration, use sync script for regular updates
5. **Backup**: Always create backups before migration (script does this automatically)

## 📁 Files Created

- `/scripts/migrate_to_aws.py` - Complete migration script with verification
- `/scripts/sync_to_aws.sh` - Quick sync utility for ongoing updates
- `/docs/AWS_MIGRATION_GUIDE.md` - Detailed migration documentation

## 🎯 Next Steps After Migration

1. Update application environment variables to use AWS resources
2. Test all API endpoints with migrated data
3. Monitor CloudWatch for any errors
4. Set up automated sync if needed (cron job)

## 💡 Pro Tips

- Always do a dry run first: `--dry-run`
- Keep local backups until migration is verified
- Use CloudWatch to monitor S3 and Aurora usage
- Consider setting up S3 lifecycle policies for old data
- Enable versioning on S3 bucket for safety

The migration preserves all data relationships and file structures, ensuring your deployed application works seamlessly with the migrated data.
