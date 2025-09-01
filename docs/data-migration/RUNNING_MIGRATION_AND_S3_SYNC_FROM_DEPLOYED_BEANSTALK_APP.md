# AWS Migration Guide: Local to Beanstalk (2-Step Process)

## Overview

This guide documents the simplified 2-step migration process for moving your local Aperilex data (PostgreSQL + files) to AWS infrastructure (Aurora + S3). The migration is split into two phases due to Aurora being in a private subnet.

## Architecture

```
STEP 1: LOCAL EXPORT                 STEP 2: BEANSTALK IMPORT
┌──────────────┐                     ┌──────────────┐
│ Local Machine│                     │EB Instance  │
│              │    S3 Bucket        │              │
│ PostgreSQL   │──────────>          │              │──> Aurora
│ Container    │          ╱          │ SSM Session  │    (Private)
│              │         ╱           │              │
│ ./data files │────────>            └──────────────┘
└──────────────┘
```

## Prerequisites

### Local Machine Requirements
- Docker running with `aperilex-postgres-1` container
- AWS CLI configured with credentials
- Python environment with dependencies (`poetry install`)
- Aurora database password

### AWS Infrastructure (Already Deployed)
- **Elastic Beanstalk**: `aperilex-backend-prod-env-c8fdf99`
- **EC2 Instance**: `i-083b20fbd26a450e9`
- **Aurora Cluster**: `tf-20250826195628596500000003` (private subnet)
- **S3 Bucket**: `aperilex-backend-filings-bucket-7ed6c88`

## Migration Scripts

We provide three migration options, from simplest to most flexible:

### Option A: Shell Scripts (Simplest)
- `migrate_step1_export.sh` - Run locally
- `migrate_step2_import.sh` - Run on Beanstalk

### Option B: Simplified Python Script
- `migrate_to_aws_simplified.py` - Streamlined for 2-step process

### Option C: Full Python Script
- `migrate_to_aws.py` - Original script with all features

## Step-by-Step Migration Process

### Step 1: Enable SSM Access (One-Time Setup)

First, enable Systems Manager access to your Beanstalk instance:

```bash
# Add SSM policy to Beanstalk instance role
aws iam attach-role-policy \
  --role-name eb-instance-role-5bfbef9 \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore \
  --region us-east-2

# Wait 5-10 minutes for SSM agent to register
# Verify SSM is ready
aws ssm describe-instance-information --region us-east-2 | grep i-083b20fbd26a450e9
```

### Step 2: Export Local Data (Run Locally)

#### Using Shell Script (Easiest):
```bash
./scripts/migrate_step1_export.sh
# Enter Aurora password when prompted
```

#### Using Python Script:
```bash
# Set Aurora password for verification
export AURORA_PASSWORD="your-aurora-password"

# Run export
python scripts/migrate_to_aws_simplified.py --export
```

#### Manual Commands:
```bash
# Export database
docker exec aperilex-postgres-1 pg_dump -U aperilex -d aperilex \
  --no-owner --no-acl --clean --if-exists > dump.sql

# Upload to S3
aws s3 cp dump.sql s3://aperilex-backend-filings-bucket-7ed6c88/migrations/

# Sync files
aws s3 sync ./data/filings s3://aperilex-backend-filings-bucket-7ed6c88/filings/
aws s3 sync ./data/analyses s3://aperilex-backend-filings-bucket-7ed6c88/analyses/
```

**Expected Output:**
```
✓ Database exported: 25.3 MB
✓ Uploaded to S3
✓ Synced filings/ to S3
✓ Synced analyses/ to S3

NEXT STEPS:
1. SSH/SSM into Beanstalk instance
2. Run import command:
   python scripts/migrate_to_aws_simplified.py --import --dump-key migrations/aperilex_db_20250828_144212.sql
```

### Step 3: Connect to Beanstalk Instance

Use AWS Systems Manager Session Manager:

```bash
aws ssm start-session --target i-083b20fbd26a450e9 --region us-east-2
```

Once connected:
```bash
# Navigate to application directory
cd /var/app/current

# Verify environment
echo $DB_HOST  # Should show Aurora endpoint
echo $AWS_S3_BUCKET  # Should show S3 bucket name
```

### Step 4: Import to Aurora (Run on Beanstalk)

#### Using Shell Script (Easiest):
```bash
# Automatically finds latest dump
./scripts/migrate_step2_import.sh

# Or specify a specific dump
./scripts/migrate_step2_import.sh migrations/aperilex_db_20250828_144212.sql
```

#### Using Python Script:
```bash
# Replace with your actual dump key from Step 2
python scripts/migrate_to_aws_simplified.py --import \
  --dump-key migrations/aperilex_db_20250828_144212.sql
```

**Expected Output:**
```
✓ Downloaded dump: 25.3 MB
✓ Database imported successfully
Verifying migration...
  companies: 150 records
  filings: 3420 records
  analyses: 892 records

✓ MIGRATION COMPLETED SUCCESSFULLY!
```

## Verification

### From Beanstalk Instance (via SSM):
```bash
# Check application health
curl http://localhost/health

# View application logs
tail -f /var/log/eb-engine.log

# Test database connection
python -c "
import os, psycopg2, json, boto3
sm = boto3.client('secretsmanager', region_name='us-east-2')
secret = json.loads(sm.get_secret_value(SecretId=os.environ['DB_PASSWORD_SECRET_ARN'])['SecretString'])
conn = psycopg2.connect(
    host=os.environ['DB_HOST'],
    database=os.environ['DB_NAME'],
    user=os.environ['DB_USER'],
    password=secret['password']
)
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM companies')
print(f'Companies: {cur.fetchone()[0]}')
"
```

### From AWS Console:
1. **Elastic Beanstalk**: Check environment health
2. **CloudWatch Logs**: Review application logs
3. **RDS Console**: Monitor Aurora metrics
4. **S3 Console**: Verify uploaded files

### From Local Machine:
```bash
# Test the deployed API
curl https://aperilex-backend-prod-env-c8fdf99.eba-3ubx3pje.us-east-2.elasticbeanstalk.com/health

# Check S3 files
aws s3 ls s3://aperilex-backend-filings-bucket-7ed6c88/ --recursive --summarize
```

## Troubleshooting

### SSM Connection Issues
```bash
# If SSM won't connect, check:
# 1. IAM policy is attached
aws iam list-attached-role-policies --role-name eb-instance-role-5bfbef9

# 2. Instance is registered with SSM (wait 5-10 minutes after adding policy)
aws ssm describe-instance-information --region us-east-2

# 3. Alternative: Use EB CLI if configured
eb ssh aperilex-backend-prod-env-c8fdf99
```

### Database Import Failures
```bash
# Check Aurora cluster status
aws rds describe-db-clusters --region us-east-2 \
  --query 'DBClusters[?DatabaseName==`aperilexdb`].Status'

# If cluster is paused, it will auto-resume on connection (wait 30-60 seconds)

# Test connection from Beanstalk
nc -zv $DB_HOST 5432
```

### S3 Access Issues
```bash
# Verify bucket exists and is accessible
aws s3 ls s3://aperilex-backend-filings-bucket-7ed6c88/

# Check IAM permissions
aws iam get-role-policy --role-name eb-instance-role-5bfbef9 \
  --policy-name backend-filings-bucket-policy-2b3d72f
```

## Script Comparison

| Feature | Shell Scripts | Simplified Python | Full Python |
|---------|--------------|-------------------|-------------|
| Lines of Code | ~100 | ~400 | ~1000 |
| Data API Support | No | No | Yes (unused) |
| Progress Bars | No | Yes | Yes |
| Error Recovery | Basic | Good | Extensive |
| Dry Run Mode | No | No | Yes |
| Best For | Quick migration | Standard use | Complex scenarios |

## Important Notes

1. **Aurora Auto-Pause**: If Aurora is paused (Serverless v2), the first connection may take 30-60 seconds
2. **Network Access**: Aurora is in a private subnet - only accessible from within VPC
3. **Data API**: Not available in us-east-2 region - use direct PostgreSQL connections
4. **File Sync**: The sync is incremental - only new/modified files are uploaded
5. **Credentials**: Database password is stored in AWS Secrets Manager

## Security Considerations

- ✅ Aurora remains in private subnet (no public access)
- ✅ Database credentials managed by Secrets Manager
- ✅ SSM provides audit logging of all sessions
- ✅ No SSH keys or passwords stored in code
- ✅ All connections use SSL/TLS encryption

## Rollback Plan

If issues occur:

1. **Database**: Aurora automatically creates snapshots
2. **S3 Files**: Enable versioning for recovery
3. **Application**: Use Elastic Beanstalk's application versions

```bash
# List Aurora snapshots
aws rds describe-db-cluster-snapshots --region us-east-2

# Restore from snapshot if needed
aws rds restore-db-cluster-from-snapshot \
  --db-cluster-identifier aperilex-restored \
  --snapshot-identifier <snapshot-id>
```

## Summary

The 2-step migration process ensures:
1. **Security**: Aurora stays in private subnet
2. **Reliability**: Clear separation of export and import phases
3. **Simplicity**: Shell scripts make it easy
4. **Flexibility**: Python scripts for advanced needs

Total migration time: ~15-20 minutes
- Export & Upload: 5-10 minutes
- Import to Aurora: 5-10 minutes
- Verification: 2-3 minutes
