# AWS Data Migration Guide for Aperilex

## Overview

This guide provides a comprehensive strategy for migrating your locally generated data (database records and file storage) to the AWS infrastructure where your Aperilex application is deployed.

## Architecture Mapping

### Local Environment
- **Database**: PostgreSQL in Docker container
- **File Storage**: Local filesystem under `./data` directory
  - `data/filings/` - SEC filing JSON documents organized by CIK
  - `data/analyses/` - Analysis results organized by CIK and filing ID
  - `data/batch_jobs/` - Batch processing job data
  - `data/batch_logs/` - Batch processing logs

### AWS Environment
- **Database**: Aurora Serverless v2 PostgreSQL cluster
- **File Storage**: S3 bucket (`aperilex-backend-filings-bucket`)
  - Same hierarchical structure as local storage
  - Uses S3StorageService implementation for consistency

## Migration Strategy

### Phase 1: Pre-Migration Verification

1. **Verify AWS Resources**
   ```bash
   # Check S3 bucket exists
   aws s3 ls s3://aperilex-backend-filings-bucket

   # Check Aurora cluster status
   aws rds describe-db-clusters --query "DBClusters[?contains(DBClusterIdentifier, 'aperilex')]"
   ```

2. **Create Backup**
   ```bash
   # Create local backup directory
   mkdir -p backups/$(date +%Y%m%d)

   # Backup local database
   docker exec aperilex-postgres-1 pg_dump -U aperilex -d aperilex > backups/$(date +%Y%m%d)/aperilex_backup.sql

   # Archive local files
   tar -czf backups/$(date +%Y%m%d)/data_files.tar.gz ./data
   ```

### Phase 2: Database Migration

#### Option A: Direct Import (Recommended for smaller datasets)

1. **Export local database**
   ```bash
   docker exec aperilex-postgres-1 pg_dump \
     -U aperilex \
     -d aperilex \
     --no-owner \
     --no-acl \
     --clean \
     --if-exists \
     > aperilex_export.sql
   ```

2. **Connect to Aurora and import**
   ```bash
   # Get Aurora endpoint and credentials
   aws rds describe-db-clusters \
     --db-cluster-identifier aperilex-db-cluster \
     --query 'DBClusters[0].Endpoint'

   # Get master password from Secrets Manager
   aws secretsmanager get-secret-value \
     --secret-id <secret-arn> \
     --query SecretString

   # Import using psql
   psql -h <aurora-endpoint> \
        -U db_admin \
        -d aperilexdb \
        -f aperilex_export.sql
   ```

#### Option B: Using Data API (For automated/scriptable approach)

1. **Enable Data API on Aurora cluster**
   ```bash
   aws rds modify-db-cluster \
     --db-cluster-identifier aperilex-db-cluster \
     --enable-http-endpoint \
     --apply-immediately
   ```

2. **Execute SQL via Data API**
   ```python
   import boto3
   import json

   rds_data = boto3.client('rds-data')

   # Read SQL file and split into statements
   with open('aperilex_export.sql', 'r') as f:
       sql_statements = f.read().split(';')

   for statement in sql_statements:
       if statement.strip():
           response = rds_data.execute_statement(
               resourceArn='<cluster-arn>',
               secretArn='<secret-arn>',
               database='aperilexdb',
               sql=statement
           )
   ```

### Phase 3: File Storage Migration

The storage structure maintains consistency between local and S3:

```
Local:                          S3:
data/                          s3://bucket/
├── filings/                   ├── filings/
│   ├── {cik}/                │   ├── {cik}/
│   │   └── {accession}.json  │   │   └── {accession}.json
├── analyses/                  ├── analyses/
│   ├── {cik}/                │   ├── {cik}/
│   │   └── {filing_id}/      │   │   └── {filing_id}/
│   │       └── {id}.json     │   │       └── {id}.json
```

1. **Sync files to S3**
   ```bash
   # Sync filings
   aws s3 sync ./data/filings/ s3://aperilex-backend-filings-bucket/filings/ \
     --exclude "*.pyc" \
     --exclude "__pycache__/*" \
     --exclude ".DS_Store"

   # Sync analyses
   aws s3 sync ./data/analyses/ s3://aperilex-backend-filings-bucket/analyses/ \
     --exclude "*.pyc" \
     --exclude "__pycache__/*" \
     --exclude ".DS_Store"

   # Optional: Sync batch data
   aws s3 sync ./data/batch_jobs/ s3://aperilex-backend-filings-bucket/batch_jobs/
   aws s3 sync ./data/batch_logs/ s3://aperilex-backend-filings-bucket/batch_logs/
   ```

2. **Verify sync**
   ```bash
   # Count local files
   find ./data/filings -name "*.json" | wc -l
   find ./data/analyses -name "*.json" | wc -l

   # Count S3 objects
   aws s3 ls s3://aperilex-backend-filings-bucket/filings/ --recursive | grep ".json" | wc -l
   aws s3 ls s3://aperilex-backend-filings-bucket/analyses/ --recursive | grep ".json" | wc -l
   ```

## Using the Migration Script

A comprehensive migration script is provided at `scripts/migrate_to_aws.py`:

### Basic Usage

```bash
# Dry run - see what would be done
python scripts/migrate_to_aws.py --dry-run

# Full migration
python scripts/migrate_to_aws.py

# Only migrate database
python scripts/migrate_to_aws.py --skip-files

# Only sync files
python scripts/migrate_to_aws.py --skip-database
```

### Script Features

1. **Automatic resource discovery** - Finds your Aurora cluster and S3 bucket
2. **Database backup** - Creates local backup before migration
3. **Progress tracking** - Shows detailed progress for all operations
4. **Verification** - Confirms data integrity after migration
5. **Rollback capability** - Keeps backups for recovery if needed

## Post-Migration Verification

### 1. Database Verification

```sql
-- Connect to Aurora
psql -h <aurora-endpoint> -U db_admin -d aperilexdb

-- Check record counts
SELECT 'companies' as table_name, COUNT(*) as count FROM companies
UNION ALL
SELECT 'filings', COUNT(*) FROM filings
UNION ALL
SELECT 'analyses', COUNT(*) FROM analyses;

-- Verify recent data
SELECT * FROM filings ORDER BY created_at DESC LIMIT 5;
SELECT * FROM analyses ORDER BY created_at DESC LIMIT 5;
```

### 2. S3 Verification

```bash
# Check file structure
aws s3 ls s3://aperilex-backend-filings-bucket/ --recursive | head -20

# Download and compare sample file
aws s3 cp s3://aperilex-backend-filings-bucket/filings/<sample-file> /tmp/
diff /tmp/<sample-file> ./data/filings/<sample-file>
```

### 3. Application Testing

1. **Update environment variables**
   ```bash
   # In production environment
   export STORAGE_SERVICE_TYPE=s3
   export AWS_S3_BUCKET=aperilex-backend-filings-bucket
   export DATABASE_URL=postgresql+asyncpg://db_admin:<password>@<aurora-endpoint>/aperilexdb
   ```

2. **Test API endpoints**
   ```bash
   # Health check
   curl https://api.aperilexlabs.com/health

   # Get filing
   curl https://api.aperilexlabs.com/api/v1/filings/<filing-id>

   # Get analysis
   curl https://api.aperilexlabs.com/api/v1/analyses/<analysis-id>
   ```

## Troubleshooting

### Common Issues

1. **Connection timeout to Aurora**
   - Ensure security group allows connections from your IP
   - Check VPC and subnet configurations
   - Verify database is not paused (Serverless v2 auto-pause)

2. **S3 access denied**
   - Verify IAM permissions for S3 bucket access
   - Check bucket policy allows your AWS credentials
   - Ensure correct region is specified

3. **Large dataset timeout**
   - Split database export into smaller chunks
   - Use batch processing for S3 sync
   - Consider using AWS Database Migration Service (DMS) for very large datasets

### Recovery

If migration fails:

1. **Restore database from backup**
   ```bash
   psql -h <aurora-endpoint> -U db_admin -d aperilexdb < backups/<date>/aperilex_backup.sql
   ```

2. **Remove synced S3 files**
   ```bash
   aws s3 rm s3://aperilex-backend-filings-bucket/ --recursive
   ```

3. **Re-run migration with fixes applied**

## Best Practices

1. **Test in staging first** - If you have a staging environment, test the migration there
2. **Schedule during low traffic** - Minimize impact on users
3. **Monitor resources** - Watch CloudWatch metrics during migration
4. **Incremental sync** - For ongoing synchronization, use incremental updates
5. **Document changes** - Keep a log of migration steps and any issues encountered

## Automation for Continuous Sync

For ongoing synchronization between local development and AWS:

```bash
#!/bin/bash
# sync_to_aws.sh - Add to cron for regular sync

# Sync only new/modified files
aws s3 sync ./data/filings/ s3://aperilex-backend-filings-bucket/filings/ \
  --exclude "*.pyc" \
  --size-only \
  --delete

aws s3 sync ./data/analyses/ s3://aperilex-backend-filings-bucket/analyses/ \
  --exclude "*.pyc" \
  --size-only \
  --delete

# Optional: Sync database changes (requires more complex logic)
# Consider using logical replication or CDC for real-time sync
```

## Security Considerations

1. **Use IAM roles** instead of access keys when possible
2. **Encrypt data in transit** - Use SSL/TLS for all connections
3. **Enable S3 encryption** - Use SSE-S3 or SSE-KMS
4. **Rotate credentials** regularly
5. **Audit access** - Enable CloudTrail for S3 and RDS access logging

## Support

For issues or questions:
1. Check CloudWatch logs for error details
2. Review Aurora Performance Insights for database issues
3. Use AWS Support if you have a support plan
4. Consult the Aperilex documentation
