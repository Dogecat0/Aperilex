"""Frontend infrastructure for Aperilex (S3, CloudFront)."""

import json
import os

import pulumi
import pulumi_aws as aws
import pulumi_aws.cloudfront as cloudfront
from gitignore_parser import parse_gitignore
from pulumi_command import local


def get_frontend_source_files() -> list[pulumi.asset.FileAsset]:
    """Get all source files in the frontend directory as Pulumi assets, filtered by .gitignore."""
    frontend_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "frontend")
    )
    gitignore_path = os.path.join(frontend_root, ".gitignore")

    if not os.path.exists(gitignore_path):
        return []  # Or handle error appropriately

    matches = parse_gitignore(gitignore_path, base_dir=frontend_root)

    assets = []
    for root, dirs, files in os.walk(frontend_root, topdown=True):
        # Prune ignored directories.
        # A copy of dirs is needed because we are modifying it in place.
        dirs[:] = [d for d in dirs if not matches(os.path.join(root, d))]

        for file in files:
            file_path = os.path.join(root, file)
            if not matches(file_path):
                assets.append(pulumi.FileAsset(file_path))

    return assets


def build_frontend() -> local.Command:
    """Build the frontend application."""
    return local.Command(
        "npm-build",
        create="npm run build",
        dir="../frontend",
        triggers=get_frontend_source_files(),
    )


def create_frontend_bucket(build_command: local.Command) -> aws.s3.Bucket:
    """Create S3 bucket for frontend hosting."""
    return aws.s3.Bucket(
        "aperilex-frontend-bucket",
        force_destroy=True,
        opts=pulumi.ResourceOptions(depends_on=[build_command]),
    )


def configure_bucket_public_access(
    bucket: aws.s3.Bucket,
) -> aws.s3.BucketPublicAccessBlock:
    """Configure bucket for public access (needed for static website hosting)."""
    return aws.s3.BucketPublicAccessBlock(
        "aperilex-frontend-bucket-public-access-block",
        bucket=bucket.id,
        block_public_acls=False,
        block_public_policy=False,
        ignore_public_acls=False,
        restrict_public_buckets=False,
    )


def configure_bucket_website(
    bucket: aws.s3.Bucket,
) -> aws.s3.BucketWebsiteConfiguration:
    """Configure S3 bucket for static website hosting."""
    return aws.s3.BucketWebsiteConfiguration(
        "aperilex-frontend-bucket-website-configuration",
        bucket=bucket.id,
        index_document=aws.s3.BucketWebsiteConfigurationIndexDocumentArgs(
            suffix="index.html"
        ),
        error_document=aws.s3.BucketWebsiteConfigurationErrorDocumentArgs(
            key="index.html"
        ),
    )


def create_bucket_policy(
    bucket: aws.s3.Bucket, public_access_block: aws.s3.BucketPublicAccessBlock
) -> aws.s3.BucketPolicy:
    """Create public read policy for the frontend bucket."""

    def public_read_policy_for_bucket(bucket_name: str) -> str:
        return json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{bucket_name}/*"],
                    }
                ],
            }
        )

    return aws.s3.BucketPolicy(
        "aperilex-frontend-bucket-policy",
        bucket=bucket.id,
        policy=bucket.id.apply(public_read_policy_for_bucket),
        opts=pulumi.ResourceOptions(depends_on=[public_access_block]),
    )


def upload_frontend_files(
    bucket: aws.s3.Bucket, build_command: local.Command
) -> local.Command:
    """Upload frontend build files to S3 bucket after build is complete."""
    return local.Command(
        "s3-sync-frontend",
        create=pulumi.Output.concat(
            "aws s3 sync ../frontend/dist s3://", bucket.id, " --delete"
        ),
        triggers=[build_command.stdout],
    )


def create_web_distribution(
    bucket: aws.s3.Bucket,
    website_config: aws.s3.BucketWebsiteConfiguration,
    cert_arn: pulumi.Input[str],
    upload_command: local.Command,
    api_domain_name: pulumi.Input[str] = None,
) -> cloudfront.Distribution:
    """Create CloudFront distribution for frontend and API routing."""

    # Base origins - always include the S3 frontend origin
    origins = [
        cloudfront.DistributionOriginArgs(
            origin_id=bucket.id,
            domain_name=website_config.website_endpoint,
            custom_origin_config=cloudfront.DistributionOriginCustomOriginConfigArgs(
                http_port=80,
                https_port=443,
                origin_protocol_policy="http-only",
                origin_ssl_protocols=["TLSv1.2"],
            ),
        )
    ]

    # Add API Gateway origin if provided
    if api_domain_name:
        origins.append(
            cloudfront.DistributionOriginArgs(
                origin_id="api-gateway",
                domain_name=api_domain_name,
                custom_origin_config=cloudfront.DistributionOriginCustomOriginConfigArgs(
                    http_port=80,
                    https_port=443,
                    origin_protocol_policy="https-only",
                    origin_ssl_protocols=["TLSv1.2"],
                ),
            )
        )

    return cloudfront.Distribution(
        "aperilex-frontend-cdn",
        enabled=True,
        origins=origins,
        default_root_object="index.html",
        default_cache_behavior=cloudfront.DistributionDefaultCacheBehaviorArgs(
            target_origin_id=bucket.id,
            viewer_protocol_policy="redirect-to-https",
            allowed_methods=["GET", "HEAD", "OPTIONS"],
            cached_methods=["GET", "HEAD", "OPTIONS"],
            forwarded_values=cloudfront.DistributionDefaultCacheBehaviorForwardedValuesArgs(
                query_string=False,
                cookies=cloudfront.DistributionDefaultCacheBehaviorForwardedValuesCookiesArgs(
                    forward="none",
                ),
            ),
            min_ttl=0,
            default_ttl=86400,
            max_ttl=31536000,
        ),
        ordered_cache_behaviors=(
            [
                cloudfront.DistributionOrderedCacheBehaviorArgs(
                    path_pattern="/api/*",
                    target_origin_id="api-gateway",
                    viewer_protocol_policy="redirect-to-https",
                    allowed_methods=[
                        "GET",
                        "HEAD",
                        "OPTIONS",
                        "PUT",
                        "POST",
                        "PATCH",
                        "DELETE",
                    ],
                    cached_methods=["GET", "HEAD", "OPTIONS"],
                    forwarded_values=cloudfront.DistributionOrderedCacheBehaviorForwardedValuesArgs(
                        query_string=True,
                        headers=["Authorization", "Content-Type", "X-Request-ID"],
                        cookies=cloudfront.DistributionOrderedCacheBehaviorForwardedValuesCookiesArgs(
                            forward="none",
                        ),
                    ),
                    min_ttl=0,
                    default_ttl=0,  # Don't cache API responses by default
                    max_ttl=0,
                    compress=True,
                )
            ]
            if api_domain_name
            else []
        ),
        price_class="PriceClass_100",
        restrictions=cloudfront.DistributionRestrictionsArgs(
            geo_restriction=cloudfront.DistributionRestrictionsGeoRestrictionArgs(
                restriction_type="none",
            ),
        ),
        viewer_certificate=cloudfront.DistributionViewerCertificateArgs(
            acm_certificate_arn=cert_arn,
            ssl_support_method="sni-only",
            minimum_protocol_version="TLSv1.2_2021",
        ),
        aliases=["aperilexlabs.com", "www.aperilexlabs.com"],
        opts=pulumi.ResourceOptions(depends_on=[upload_command]),
    )
