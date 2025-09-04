"""High-level orchestration functions for infrastructure components."""

from collections.abc import Awaitable
from typing import Any, cast

import pulumi
import pulumi_aws as aws
from api_gateway import (
    create_api_integration,
    create_api_route,
    create_api_stage,
    create_http_api,
)
from backend import (
    attach_custom_policies,
    attach_eb_managed_policies,
    build_and_push_docker_image,
    create_app_version,
    create_backend_app_bucket,
    create_backend_filings_bucket,
    create_backend_source_bundle,
    create_db_secret_policy,
    create_eb_application,
    create_eb_environment,
    create_eb_instance_role,
    create_ecr_repository,
    create_filings_bucket_policy,
    create_instance_profile,
)
from certificates import create_domain_certificate
from database import create_aurora_cluster, create_db_subnet_group
from networking import (
    associate_subnet_with_route_table,
    create_db_security_group,
    create_eb_security_group,
    create_internet_gateway,
    create_private_route_table,
    create_private_subnet,
    create_public_route_table,
    create_public_subnet,
    create_vpc,
)

from frontend import (
    build_frontend,
    configure_bucket_public_access,
    configure_bucket_website,
    create_bucket_policy,
    create_frontend_bucket,
    create_web_distribution,
    upload_frontend_files,
)


class InfrastructureResources:
    """Container for networking infrastructure resources."""

    def __init__(self) -> None:
        # Networking
        self.vpc: aws.ec2.Vpc
        self.public_subnets: list[aws.ec2.Subnet] = []
        self.private_subnets: list[aws.ec2.Subnet] = []
        self.eb_security_group: aws.ec2.SecurityGroup
        self.db_security_group: aws.ec2.SecurityGroup


def setup_certificate(
    us_east_1_provider: aws.Provider,
) -> aws.acm.CertificateValidation:
    """Set up SSL certificate for the domain (used by CloudFront)."""
    return create_domain_certificate(us_east_1_provider)


def setup_networking() -> InfrastructureResources:
    """Set up VPC, subnets, and security groups."""
    resources = InfrastructureResources()

    # Create VPC
    resources.vpc = create_vpc()

    # Get availability zones
    azs = aws.get_availability_zones(state="available")

    # Create subnets
    public_subnet_1 = create_public_subnet(
        resources.vpc.id, "10.0.1.0/24", azs.names[0], "aperilex-public-subnet-1"
    )
    public_subnet_2 = create_public_subnet(
        resources.vpc.id, "10.0.2.0/24", azs.names[1], "aperilex-public-subnet-2"
    )
    private_subnet_1 = create_private_subnet(
        resources.vpc.id, "10.0.3.0/24", azs.names[0], "aperilex-private-subnet-1"
    )
    private_subnet_2 = create_private_subnet(
        resources.vpc.id, "10.0.4.0/24", azs.names[1], "aperilex-private-subnet-2"
    )

    resources.public_subnets = [public_subnet_1, public_subnet_2]
    resources.private_subnets = [private_subnet_1, private_subnet_2]

    # Create internet gateway and route tables
    internet_gateway = create_internet_gateway(resources.vpc.id)
    public_route_table = create_public_route_table(
        resources.vpc.id, internet_gateway.id
    )
    private_route_table = create_private_route_table(resources.vpc.id)

    # Associate subnets with route tables
    associate_subnet_with_route_table(
        public_subnet_1.id, public_route_table.id, "public-rta-1"
    )
    associate_subnet_with_route_table(
        public_subnet_2.id, public_route_table.id, "public-rta-2"
    )
    associate_subnet_with_route_table(
        private_subnet_1.id, private_route_table.id, "private-rta-1"
    )
    associate_subnet_with_route_table(
        private_subnet_2.id, private_route_table.id, "private-rta-2"
    )

    # Create security groups
    resources.eb_security_group = create_eb_security_group(resources.vpc.id)
    resources.db_security_group = create_db_security_group(
        resources.vpc.id, resources.eb_security_group.id
    )

    return resources


def setup_database(networking_resources: InfrastructureResources) -> aws.rds.Cluster:
    """Set up Aurora database cluster."""
    private_subnet_ids = [subnet.id for subnet in networking_resources.private_subnets]
    db_subnet_group = create_db_subnet_group(
        cast("list[str | Awaitable[str] | pulumi.Output[str]]", private_subnet_ids)
    )
    db_cluster, db_instance = create_aurora_cluster(
        db_subnet_group.name, networking_resources.db_security_group.id
    )
    # Return just the cluster to maintain compatibility
    return db_cluster


def setup_frontend(
    domain_certificate: aws.acm.CertificateValidation,
    api_gateway: aws.apigatewayv2.Api | None = None,
) -> tuple[
    aws.s3.Bucket, aws.s3.BucketWebsiteConfiguration, aws.cloudfront.Distribution
]:
    """Set up frontend S3 bucket and CloudFront distribution."""
    build_command = build_frontend()
    frontend_bucket = create_frontend_bucket(build_command)
    frontend_public_access = configure_bucket_public_access(frontend_bucket)
    frontend_website_config = configure_bucket_website(frontend_bucket)
    _ = create_bucket_policy(frontend_bucket, frontend_public_access)

    # Upload frontend files
    upload_command = upload_frontend_files(frontend_bucket, build_command)

    # Create CloudFront distribution
    api_domain_name: pulumi.Input[str] | None = None
    if api_gateway:
        # Extract domain from API Gateway's invoke URL (remove https:// and /stage)
        api_domain_name = api_gateway.api_endpoint.apply(
            lambda endpoint: endpoint.replace("https://", "").split("/")[0]
        )

    web_distribution = create_web_distribution(
        frontend_bucket,
        frontend_website_config,
        domain_certificate.certificate_arn,
        upload_command,
        api_domain_name,
    )

    return frontend_bucket, frontend_website_config, web_distribution


def setup_backend(
    networking_resources: InfrastructureResources,
    db_cluster: aws.rds.Cluster,
    env_vars: dict[str, Any],
) -> tuple[aws.s3.Bucket, aws.s3.Bucket, aws.elasticbeanstalk.Environment]:
    """Set up backend infrastructure including ECR, Elastic Beanstalk, and IAM."""
    # Create backend buckets
    backend_app_bucket = create_backend_app_bucket()
    backend_filings_bucket = create_backend_filings_bucket()

    # Create ECR and build image
    ecr_repo = create_ecr_repository()
    backend_image = build_and_push_docker_image(ecr_repo)

    # Create source bundle in memory
    source_bundle = create_backend_source_bundle(backend_image)

    # Create IAM resources
    eb_role = create_eb_instance_role()
    _ = attach_eb_managed_policies(eb_role)
    filings_policy = create_filings_bucket_policy(backend_filings_bucket)
    db_secret_policy = create_db_secret_policy(db_cluster)
    _ = attach_custom_policies(eb_role, [filings_policy, db_secret_policy])
    instance_profile = create_instance_profile(eb_role)

    # Create Elastic Beanstalk resources
    eb_app = create_eb_application()
    app_version = create_app_version(eb_app, backend_app_bucket, source_bundle)

    public_subnet_ids = [subnet.id for subnet in networking_resources.public_subnets]
    eb_env = create_eb_environment(
        eb_app,
        app_version,
        instance_profile,
        eb_role,
        networking_resources.vpc.id,
        cast("list[str | Awaitable[str] | pulumi.Output[str]]", public_subnet_ids),
        networking_resources.eb_security_group.id,
        env_vars,
        db_cluster,
        backend_filings_bucket,
        backend_image,
    )

    return backend_app_bucket, backend_filings_bucket, eb_env


def setup_api_gateway(eb_env: aws.elasticbeanstalk.Environment) -> aws.apigatewayv2.Api:
    """Set up API Gateway without custom domain (will use CloudFront for routing)."""
    api = create_http_api()
    api_integration = create_api_integration(api, eb_env.cname)
    api_route = create_api_route(api, api_integration)
    _ = create_api_stage(api, api_route)

    return api


def create_dns_records(
    zone_labs: aws.route53.Zone,
    web_distribution: aws.cloudfront.Distribution,
) -> None:
    """Create Route53 DNS records for the domain (frontend + API through CloudFront)."""
    # Main domain record - update to point to CloudFront
    aws.route53.Record(
        "aperilexlabs_record",
        zone_id=zone_labs.zone_id,
        name="aperilexlabs.com",
        type="A",
        aliases=[
            aws.route53.RecordAliasArgs(
                name=web_distribution.domain_name,
                zone_id=web_distribution.hosted_zone_id,
                evaluate_target_health=False,
            ),
        ],
    )

    # WWW record
    aws.route53.Record(
        "www_aperilexlabs_record",
        zone_id=zone_labs.zone_id,
        name="www.aperilexlabs.com",
        type="A",
        aliases=[
            aws.route53.RecordAliasArgs(
                name=web_distribution.domain_name,
                zone_id=web_distribution.hosted_zone_id,
                evaluate_target_health=False,
            ),
        ],
    )


def export_outputs(
    frontend_bucket: aws.s3.Bucket,
    frontend_website_config: aws.s3.BucketWebsiteConfiguration,
    web_distribution: aws.cloudfront.Distribution,
    db_cluster: aws.rds.Cluster,
    eb_env: aws.elasticbeanstalk.Environment,
    backend_filings_bucket: aws.s3.Bucket,
    api: aws.apigatewayv2.Api,
) -> None:
    """Export all infrastructure outputs."""
    # Frontend exports
    pulumi.export("frontend_bucket_name", frontend_bucket.id)
    pulumi.export("frontend_website_endpoint", frontend_website_config.website_endpoint)
    pulumi.export("web_distribution_url", web_distribution.domain_name)

    # Database exports
    pulumi.export("db_cluster_endpoint", db_cluster.endpoint)
    pulumi.export("db_cluster_reader_endpoint", db_cluster.reader_endpoint)
    pulumi.export(
        "db_cluster_master_user_secret_arn",
        db_cluster.master_user_secrets[0].secret_arn,
    )

    # Backend exports
    pulumi.export("backend_environment_url", eb_env.cname)
    pulumi.export("backend_filings_bucket_name", backend_filings_bucket.id)

    # API exports
    pulumi.export("api_invoke_url", api.api_endpoint)
    pulumi.export("api_url", "https://aperilexlabs.com/api")
