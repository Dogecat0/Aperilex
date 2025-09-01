# Production Fixes - 2025-08-28

## Summary

Fixed three critical issues affecting the production deployment at www.aperilexlabs.com:

1. Individual analysis page returning 500 errors
2. Filing pages not showing analysis results properly
3. Start Analysis button showing false progress instead of disabled message

## Issues and Root Causes

### Issue 1: Individual Analysis Page 500 Error

**Symptom**: `GET /api/analyses/{id}` returning 500 Internal Server Error

**Root Cause**: Two separate issues:

1. **Storage configuration mismatch**
   - `analysis_tasks.py` used `USE_S3_STORAGE` environment variable (not set)
   - Settings used `STORAGE_SERVICE_TYPE=s3`
   - This caused the code to look in local storage instead of S3

2. **S3 file extension mismatch** (discovered after first fix)
   - Migration script stored files WITH `.json` extension in S3
   - Retrieval code didn't add `.json` when fetching
   - Example: S3 has `analysis_8d95578e-aa32-4f5e-a225-e6cff9c64ee5.json`
   - Code looked for: `analysis_8d95578e-aa32-4f5e-a225-e6cff9c64ee5` (no extension)

**Fix 1**: Modified `analysis_tasks.py` to use Settings consistently:

```python
# Before:
USE_S3_STORAGE = os.getenv("USE_S3_STORAGE", "false").lower() == "true"

# After:
_settings = Settings()
USE_S3_STORAGE = _settings.storage_service_type == "s3"
```

**Fix 2**: Added `.json` extension when retrieving from S3:

```python
# In analysis_tasks.py get_analysis_results():
# Before:
analysis_results = await s3_service.get(analysis_key)

# After:
analysis_results = await s3_service.get(f"{analysis_key}.json")

# Also in get_filing_content():
# Before:
filing_content = await s3_service.get(clean_accession)

# After:
filing_content = await s3_service.get(f"{clean_accession}.json")
```

### Issue 2: Filing Page Not Showing Analysis

**Symptom**: Filing pages show "No Analysis Available" even when analysis exists

**Root Cause**: Same as Issue 1 - both storage configuration and file extension mismatches

- The filing page retrieves analysis via `get_by_filing_id_with_results()`
- This also uses the same flawed `USE_S3_STORAGE` check
- Results in S3 were not being found due to missing `.json` extension

**Fix**: Same as Issue 1 - both the configuration fix and `.json` extension fix resolve this issue

### Issue 3: Start Analysis Button Behavior

**Symptom**: Clicking "Start Analysis" shows false progress instead of disabled message

**Root Cause**: No check for demo mode

- The `/analyze` endpoint was processing requests normally
- It would fail due to messaging service issues but show progress first

**Fix**: Added feature flag and check:

```python
# In settings.py:
analysis_enabled: bool = Field(
    default=True,
    validation_alias="ANALYSIS_ENABLED",
    description="Whether filing analysis is enabled (set to False for demo mode)",
)

# In filings.py analyze_filing endpoint:
settings = Settings()
if not settings.analysis_enabled:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Analysis is disabled for demonstration purposes. Try to view one of the complete analysis reports.",
    )
```

## Required Environment Variables

For production deployment, set these environment variables:

```bash
# Storage Configuration
STORAGE_SERVICE_TYPE=s3
AWS_S3_BUCKET=your-bucket-name
AWS_REGION=us-east-2

# Messaging Configuration (disabled for demo)
QUEUE_SERVICE_TYPE=mock
WORKER_SERVICE_TYPE=mock

# Feature Flags
ANALYSIS_ENABLED=false  # Set to true when ready for production analysis

# Database
DATABASE_URL=postgresql://...
```

## Deployment Steps

### 1. Update Environment Variables

```bash
# Create config file
cat > /tmp/env_update.json << 'EOF'
[
  {
    "Namespace": "aws:elasticbeanstalk:application:environment",
    "OptionName": "ANALYSIS_ENABLED",
    "Value": "false"
  }
]
EOF

# Apply to Elastic Beanstalk
aws elasticbeanstalk update-environment \
  --environment-name your-env-name \
  --region us-east-2 \
  --option-settings file:///tmp/env_update.json
```

### 2. Deploy Code Changes

```bash
# Commit changes
git add -A
git commit -m "Fix storage configuration and add demo mode for analysis"

# Deploy to Elastic Beanstalk
eb deploy
```

### 3. Verify Fixes

```bash
# Test individual analysis endpoint
curl -s "https://www.aperilexlabs.com/api/analyses/8d95578e-aa32-4f5e-a225-e6cff9c64ee5" | jq '.analysis_id'

# Test filing page with analysis
curl -s "https://www.aperilexlabs.com/api/filings/0000320193-25-000073" | jq '.analyses_count'

# Test analyze endpoint (should return 403)
curl -X POST "https://www.aperilexlabs.com/api/filings/0000320193-25-000073/analyze" \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n"
```

## Important Notes

### Why the S3 Extension Fix is in analysis_tasks.py

The fix for the `.json` extension is intentionally placed in `analysis_tasks.py` rather than in the `S3StorageService` because:

1. **S3StorageService is generic**: It's used for various storage needs (cache, locks, tasks, etc.), not just JSON files
2. **Migration-specific issue**: The `.json` extension was added during migration, not a design requirement
3. **Targeted fix**: Only filing and analysis retrieval need the extension, not all S3 operations
4. **Avoid breaking other features**: Modifying S3StorageService to always add `.json` would break caching and other non-file storage

### Why Both SQS and Analysis Need to be Disabled

1. **SQS Disabled**: Prevents initialization errors on ALL endpoints

   - Messaging system initializes on every request
   - Without proper IAM permissions, this causes 500 errors

2. **Analysis Disabled**: Provides proper user experience
   - Returns meaningful error message
   - Prevents false progress indicators

### Future Production Enablement

When ready to enable analysis in production:

1. **Option A: Add IAM Permissions**

   ```python
   # Add to EB instance role
   "sqs:ListQueues"
   "sqs:GetQueueUrl"
   "sqs:SendMessage"
   "sqs:ReceiveMessage"
   "sqs:DeleteMessage"
   ```

2. **Option B: Keep Mock Services**

   - If background processing not needed
   - Simpler architecture for demo/MVP

3. **Option C: Lazy Initialization**
   - Modify code to only initialize messaging when needed
   - More complex but efficient

## Testing Checklist

- [x] `/api/analyses` - Lists analyses correctly
- [x] `/api/analyses/{id}` - Returns individual analysis with results
- [x] `/api/filings/{accession}` - Shows analysis count
- [x] `/api/filings/{accession}/analysis` - Returns analysis results
- [x] POST `/api/filings/{accession}/analyze` - Returns 403 with proper message

## Related Documentation

- [SQS_INITIALIZATION_FIX_2025-08-28.md](./SQS_INITIALIZATION_FIX_2025-08-28.md) - Initial SQS fix
- [S3_STORAGE_ISSUE_ANALYSIS.md](./S3_STORAGE_ISSUE_ANALYSIS.md) - S3 file extension issue

## Lessons Learned

1. **Configuration Consistency**: Always use centralized Settings class, avoid direct env var access
2. **Feature Flags**: Essential for demo deployments
3. **Lazy Initialization**: Services should initialize only when needed
4. **Error Messages**: Provide meaningful user feedback in demo mode
5. **Testing**: Test all API endpoints after deployment changes
6. **File Extensions**: Be consistent with file extensions during migration and retrieval
7. **Storage Abstraction**: Keep storage services generic; handle file-specific logic at the application level
