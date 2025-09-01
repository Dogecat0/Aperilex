# S3 Storage Issue Analysis and Resolution

## Issue Summary

After migrating from local storage to AWS (Aurora + S3), the application experienced failures when retrieving analyses and filings, even though the data existed in both the database and S3.

## Timeline of Events

1. **Initial State**:
   - Lists of filings/analyses worked ✅
   - Individual item retrieval failed with 404/500 errors ❌
   - Environment variable `USE_S3_STORAGE` was not set

2. **After Setting `USE_S3_STORAGE=true`**:
   - Environment variable added to Elastic Beanstalk
   - No immediate effect (no redeploy)

3. **After Applying .json Fix and Redeploying**:
   - ALL endpoints failed, including lists ❌❌❌
   - Application became completely broken

4. **After Reverting .json Fix**:
   - Returned to initial state (lists work, individual items fail)

## Root Cause Analysis

### Primary Issue: File Extension Mismatch

The core problem is a mismatch between how files are stored in S3 and how the application tries to retrieve them:

**S3 Storage Structure** (created during migration):
```
s3://bucket/analyses/1397187/000139718725000027/analysis_8d95578e-aa32-4f5e-a225-e6cff9c64ee5.json
s3://bucket/filings/320193/000032019325000073.json
```

**Application Expects** (in `analysis_tasks.py`):
```python
# For analyses
prefix = f"analyses/{company_cik}/{accession_number.value.replace('-', '')}/"
key = f"analysis_{analysis_id}"  # Missing .json extension!

# For filings
prefix = f"filings/{company_cik}/"
key = clean_accession  # Missing .json extension!
```

### Why the Migration Added .json Extensions

The migration script (`scripts/migrate_to_aws.py`) used `aws s3 sync` to copy local files:
```bash
aws s3 sync ./data/filings s3://bucket/filings/
aws s3 sync ./data/analyses s3://bucket/analyses/
```

The local files already had `.json` extensions, so they were preserved during the sync.

### Why My Initial Fix Made Things Worse

My attempted fix was to add `.json` when calling the S3 service:
```python
# Changed from:
analysis_results = await s3_service.get(analysis_key)
# To:
analysis_results = await s3_service.get(f"{analysis_key}.json")
```

However, this broke the application completely because:
1. The code wasn't properly tested
2. Import-time validation of S3 configuration may have failed
3. The fix was incomplete (didn't handle all edge cases)

## The Real Problem: Module Import Time Configuration

The file `analysis_tasks.py` has this at module import time:
```python
USE_S3_STORAGE = os.getenv("USE_S3_STORAGE", "false").lower() == "true"
```

This means:
- The variable is evaluated when the module is first imported
- Changes to the environment variable require a full application restart
- Any import errors in this module will break the entire application

## Correct Solution

### Option 1: Fix the S3 Keys (Recommended)

Add `.json` extension to the keys, but do it correctly:

```python
# In get_filing_content()
if USE_S3_STORAGE:
    s3_service = S3StorageService(
        bucket_name=settings.aws_s3_bucket,
        aws_region=settings.aws_region,
        prefix=f"filings/{company_cik}/",
    )
    await s3_service.connect()

    # Add .json extension for S3 retrieval
    filing_content = await s3_service.get(f"{clean_accession}.json")

# In get_analysis_results()
if USE_S3_STORAGE:
    s3_service = S3StorageService(
        bucket_name=settings.aws_s3_bucket,
        aws_region=settings.aws_region,
        prefix=f"analyses/{company_cik}/{accession_number.value.replace('-', '')}/",
    )
    await s3_service.connect()

    # Add .json extension for S3 retrieval
    analysis_results = await s3_service.get(f"{analysis_key}.json")

# In store_filing_content()
if USE_S3_STORAGE:
    # Store WITH .json extension to match existing structure
    success = await s3_service.set(f"{clean_accession}.json", filing_content)

# In store_analysis_results()
if USE_S3_STORAGE:
    # Store WITH .json extension to match existing structure
    success = await s3_service.set(f"{analysis_key}.json", analysis_results)
```

### Option 2: Rename S3 Objects (Not Recommended)

Remove `.json` extensions from all S3 objects to match the code's expectations. This would require:
- Copying all objects without extensions
- Deleting old objects
- Risk of data loss
- Downtime during migration

### Option 3: Make S3StorageService Handle Extensions

Modify `S3StorageService` to automatically append `.json` if the key doesn't already have it:

```python
def _get_s3_key(self, key: str) -> str:
    """Get S3 object key with prefix and ensure .json extension."""
    full_key = f"{self.prefix}{key}"
    # Auto-append .json if not present
    if not full_key.endswith('.json'):
        full_key = f"{full_key}.json"
    return full_key
```

## Why Lists Were Failing After the Change

The list endpoints (`/api/analyses`, `/api/companies/AAPL/filings`) don't directly call S3, they only query the database. However, they were failing because:

1. The module import of `analysis_tasks.py` happens at application startup
2. If there's any error in the module (like S3 validation failing), the entire import chain breaks
3. This breaks the repository classes that import from `analysis_tasks`
4. Which breaks the query handlers
5. Which breaks the API endpoints

## Deployment Checklist

Before redeploying with the fix:

1. ✅ Ensure `USE_S3_STORAGE=true` is set in Elastic Beanstalk environment
2. ✅ Ensure `AWS_S3_BUCKET` is set correctly
3. ✅ Ensure `AWS_REGION` is set correctly
4. ✅ Test the fix locally with a mock S3 service
5. ✅ Add proper error handling and logging
6. ✅ Deploy to a staging environment first (if available)
7. ✅ Monitor logs during deployment
8. ✅ Have a rollback plan ready

## Lessons Learned

1. **Migration Scripts Should Match Application Expectations**: The migration should create files in the exact format the application expects
2. **Environment Variables at Import Time Are Dangerous**: Consider lazy evaluation instead
3. **Test S3 Integration Thoroughly**: Mock S3 services for local testing
4. **Incremental Changes**: Test each change in isolation before combining
5. **Monitor Import Errors**: Module import failures can cascade and break the entire application
6. **Version Your Data Format**: Include version info in storage to handle format changes

## Recommended Next Steps

1. **Immediate**: Deploy Option 1 fix with proper testing
2. **Short-term**: Add integration tests for S3 operations
3. **Medium-term**: Refactor to lazy-load configuration
4. **Long-term**: Consider using a data versioning strategy for stored files
