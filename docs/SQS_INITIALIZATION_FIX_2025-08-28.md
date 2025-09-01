# SQS Initialization Issue - Root Cause Analysis and Fix

## Issue Summary

After reverting S3 storage changes, the application continued to return 500 errors for all API endpoints, even though the S3 issue had been addressed. The root cause was an unrelated SQS permissions issue that was preventing the application from initializing.

## Timeline of Events

1. **Initial State (Before S3 changes)**:
   - Lists of filings/analyses worked ✅
   - Individual item retrieval failed ❌
2. **After S3 changes and revert**:

   - ALL endpoints failed with 500 errors ❌
   - Even after removing `USE_S3_STORAGE=true` and reverting .json extension changes

3. **2025-08-28 17:27 UTC**:
   - Applied SQS fix
   - All endpoints working again ✅

## Root Cause Analysis

### The Real Problem

The application was trying to initialize AWS SQS messaging services on startup, but the EC2 instance IAM role lacked the necessary permissions:

```
botocore.exceptions.ClientError: An error occurred (AccessDenied) when calling the ListQueues operation:
User: arn:aws:sts::727596873740:assumed-role/eb-instance-role-5bfbef9/i-083b20fbd26a450e9
is not authorized to perform: sqs:listqueues on resource: arn:aws:sqs:us-east-2:727596873740:
```

### Why SQS Was Being Initialized

1. **Environment Detection**: The application was deployed with `ENVIRONMENT=production`

2. **Automatic Service Selection**: In `src/shared/config/settings.py`:

   ```python
   def _get_default_queue_service() -> str:
       """Determine default queue service type based on environment."""
       if _is_testing():
           return "mock"
       env = os.environ.get("ENVIRONMENT", "development").lower()
       return "sqs" if env == "production" else "rabbitmq"  # <-- Automatically uses SQS in production
   ```

3. **Initialization Chain**:
   - Any API request → `ServiceFactory.get_handler_dependencies()`
   - → Creates `BackgroundTaskCoordinator`
   - → Calls `ensure_messaging_initialized()`
   - → Tries to connect to SQS
   - → Fails with permission error
   - → Returns 500 error

### Why This Wasn't a Problem Before

The messaging system initialization was likely added recently but wasn't being used:

- No background tasks are actually being executed
- The `/analyze` endpoint (which would use background tasks) isn't being called
- Local development has RabbitMQ and worker services completely commented out in docker-compose.yml

## Investigation Process

### 1. Retrieved AWS Logs

```bash
aws ssm send-command --instance-ids "i-083b20fbd26a450e9" \
  --document-name "AWS-RunShellScript" \
  --parameters '{"commands":["docker logs $(docker ps -q | head -1) 2>&1 | tail -50"]}' \
  --region us-east-2
```

### 2. Identified SQS Error

Found repeated errors:

```
Failed to connect to AWS SQS: An error occurred (AccessDenied) when calling the ListQueues operation
Failed to initialize messaging services
Failed to list analyses
```

### 3. Verified Messaging Not In Use

- Checked docker-compose.yml: RabbitMQ and worker services commented out (lines 19-33, 75-124)
- Verified no calls to `/analyze` endpoint in production logs
- Confirmed local development works without any messaging services

### 4. Checked Environment Configuration

```bash
aws elasticbeanstalk describe-configuration-settings \
  --application-name aperilex-backend-app \
  --environment-name aperilex-backend-prod-env-c8fdf99 \
  --region us-east-2
```

Found:

- `ENVIRONMENT=production` was set
- No `QUEUE_SERVICE_TYPE` override (defaults to SQS in production)
- No `WORKER_SERVICE_TYPE` override (defaults to lambda in production)

## The Fix

### Solution: Disable SQS/Messaging Services

Since the application doesn't currently use background tasks or messaging, the solution was to explicitly disable these services.

### Implementation

Created environment variable overrides:

```json
[
  {
    "Namespace": "aws:elasticbeanstalk:application:environment",
    "OptionName": "QUEUE_SERVICE_TYPE",
    "Value": "mock"
  },
  {
    "Namespace": "aws:elasticbeanstalk:application:environment",
    "OptionName": "WORKER_SERVICE_TYPE",
    "Value": "mock"
  },
  {
    "Namespace": "aws:elasticbeanstalk:application:environment",
    "OptionName": "STORAGE_SERVICE_TYPE",
    "Value": "s3"
  }
]
```

Applied to Elastic Beanstalk:

```bash
aws elasticbeanstalk update-environment \
  --environment-name aperilex-backend-prod-env-c8fdf99 \
  --region us-east-2 \
  --option-settings file:///tmp/disable_sqs.json
```

### Result

✅ All API endpoints now working:

- `/api/analyses` - 200 OK
- `/api/companies/AAPL/filings` - 200 OK
- No more SQS initialization errors

## Alternative Solution (Not Implemented)

If background tasks were actually needed, the alternative would be to add SQS permissions to the IAM role:

```python
def create_sqs_policy() -> aws.iam.Policy:
    """Create IAM policy for SQS operations."""
    return aws.iam.Policy(
        "eb-sqs-policy",
        description="Allow EB instances to use SQS",
        policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": [
                    "sqs:ListQueues",
                    "sqs:GetQueueUrl",
                    "sqs:SendMessage",
                    "sqs:ReceiveMessage",
                    "sqs:DeleteMessage",
                ],
                "Resource": "*"
            }]
        })
    )
```

## Lessons Learned

1. **Environment-Specific Defaults Can Be Dangerous**: The automatic service selection based on `ENVIRONMENT` caused unexpected behavior in production.

2. **Unused Services Should Be Explicitly Disabled**: Even if a service isn't being used, its initialization can cause failures.

3. **IAM Permissions Must Match Service Requirements**: If a service is enabled (even inadvertently), the IAM role must have the necessary permissions.

4. **Error Messages Can Be Misleading**: The 500 errors appeared after the S3 changes, but were actually caused by an unrelated SQS issue that was always present but only triggered after the redeploy.

5. **Local vs Production Parity**: The local environment had messaging disabled, but production tried to enable it automatically.

## Recommendations

### Immediate Actions

- ✅ Applied: Disabled SQS/messaging services via environment variables
- Monitor application to ensure no functionality is affected

### Future Improvements

1. **Explicit Service Configuration**: Always explicitly set service types in production rather than relying on defaults:

   ```bash
   QUEUE_SERVICE_TYPE=mock  # or "sqs" when needed
   WORKER_SERVICE_TYPE=mock  # or "lambda" when needed
   STORAGE_SERVICE_TYPE=s3
   ```

2. **Lazy Initialization**: Consider modifying the code to only initialize messaging services when actually needed, not on every request.

3. **Health Check Improvements**: Add a health check that validates all required services can be initialized.

4. **When Enabling Background Tasks**:
   - First add IAM permissions for SQS
   - Create SQS queues in AWS
   - Update environment variables to use "sqs" instead of "mock"
   - Deploy worker services to process the queue

## Verification Commands

Check if the fix is working:

```bash
# Test analyses endpoint
curl -s "https://www.aperilexlabs.com/api/analyses?page=1&page_size=3" -w "\nHTTP Status: %{http_code}\n"

# Test company filings endpoint
curl -s "https://www.aperilexlabs.com/api/companies/AAPL/filings?page=1&page_size=5" -w "\nHTTP Status: %{http_code}\n"
```

Both should return HTTP Status: 200

## Related Issues

- Previous issue: [S3_STORAGE_ISSUE_ANALYSIS.md](./S3_STORAGE_ISSUE_ANALYSIS.md) - File extension mismatch in S3 storage
- Current issue: SQS initialization failures due to missing IAM permissions (this document)
