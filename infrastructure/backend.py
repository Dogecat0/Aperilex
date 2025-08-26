"""Backend infrastructure for Aperilex (Elastic Beanstalk, ECR, IAM)."""

import json
from typing import Any

import pulumi
import pulumi_aws as aws
import pulumi_docker as docker


def create_backend_app_bucket() -> aws.s3.Bucket:
    """Create S3 bucket to store application source code bundles."""
    return aws.s3.Bucket(
        "aperilex-backend-app-versions",
        force_destroy=True,
    )


def create_backend_filings_bucket() -> aws.s3.Bucket:
    """Create S3 bucket for backend application to store filings."""
    return aws.s3.Bucket(
        "aperilex-backend-filings-bucket",
        force_destroy=True,
    )


def create_ecr_repository() -> aws.ecr.Repository:
    """Create ECR repository for the backend Docker image."""
    return aws.ecr.Repository(
        "aperilex-backend-ecr",
        image_tag_mutability="MUTABLE",
        image_scanning_configuration=aws.ecr.RepositoryImageScanningConfigurationArgs(
            scan_on_push=True,
        ),
        force_delete=True,
        opts=pulumi.ResourceOptions(protect=True),
    )


def build_and_push_docker_image(ecr_repo: aws.ecr.Repository) -> docker.Image:
    """Build and push Docker image to ECR."""
    ecr_auth_token = aws.ecr.get_authorization_token_output(
        registry_id=ecr_repo.registry_id
    )

    return docker.Image(
        "aperilex-backend-image",
        image_name=ecr_repo.repository_url.apply(lambda url: f"{url}:latest"),
        build={
            "context": "../",
            "dockerfile": "../Dockerfile",
        },
        skip_push=False,
        registry=docker.RegistryArgs(
            server=ecr_repo.repository_url,
            username=ecr_auth_token.user_name,
            password=ecr_auth_token.password,
        ),
        opts=pulumi.ResourceOptions(protect=True),
    )


def create_backend_source_bundle(
    backend_image: docker.Image,
) -> pulumi.Output[pulumi.asset.AssetArchive]:
    """Create a zip archive with Dockerrun.aws.json in memory."""
    return backend_image.image_name.apply(
        lambda image_full_name: pulumi.asset.AssetArchive(
            {
                "Dockerrun.aws.json": pulumi.asset.StringAsset(
                    json.dumps(
                        {
                            "AWSEBDockerrunVersion": "1",
                            "Image": {"Name": image_full_name, "Update": "true"},
                            "Ports": [{"ContainerPort": 8000}],
                        }
                    )
                )
            }
        )
    )


def create_eb_instance_role() -> aws.iam.Role:
    """Create IAM role for EC2 instances in Elastic Beanstalk."""
    return aws.iam.Role(
        "eb-instance-role",
        assume_role_policy=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": "sts:AssumeRole",
                        "Effect": "Allow",
                        "Principal": {"Service": "ec2.amazonaws.com"},
                    }
                ],
            }
        ),
    )


def attach_eb_managed_policies(
    role: aws.iam.Role,
) -> list[aws.iam.RolePolicyAttachment]:
    """Attach AWS managed policies to Elastic Beanstalk role."""
    return [
        aws.iam.RolePolicyAttachment(
            "eb-webtier-policy-attachment",
            role=role.name,
            policy_arn="arn:aws:iam::aws:policy/AWSElasticBeanstalkWebTier",
        ),
        aws.iam.RolePolicyAttachment(
            "eb-docker-policy-attachment",
            role=role.name,
            policy_arn="arn:aws:iam::aws:policy/AWSElasticBeanstalkMulticontainerDocker",
        ),
        aws.iam.RolePolicyAttachment(
            "eb-ecr-policy-attachment",
            role=role.name,
            policy_arn="arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
        ),
    ]


def create_filings_bucket_policy(filings_bucket: aws.s3.Bucket) -> aws.iam.Policy:
    """Create IAM policy for backend to access filings bucket."""
    policy_document = filings_bucket.arn.apply(
        lambda arn: json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["s3:GetObject", "s3:ListBucket"],
                        "Resource": [arn, f"{arn}/*"],
                    }
                ],
            }
        )
    )

    return aws.iam.Policy(
        "backend-filings-bucket-policy",
        description="Policy for the backend to access the filings bucket",
        policy=policy_document,
    )


def create_db_secret_policy(db_cluster: aws.rds.Cluster) -> aws.iam.Policy:
    """Create IAM policy to read database secrets."""
    return aws.iam.Policy(
        "db-secret-read-policy",
        description="Allow EB to read the database master user secret",
        policy=db_cluster.master_user_secrets[0].secret_arn.apply(
            lambda arn: json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": "secretsmanager:GetSecretValue",
                            "Resource": arn,
                        }
                    ],
                }
            )
        ),
    )


def attach_custom_policies(
    role: aws.iam.Role, policies: list[aws.iam.Policy]
) -> list[aws.iam.RolePolicyAttachment]:
    """Attach custom policies to the role."""
    attachments = []
    for i, policy in enumerate(policies):
        attachment = aws.iam.RolePolicyAttachment(
            f"eb-custom-policy-attachment-{i}",
            role=role.name,
            policy_arn=policy.arn,
        )
        attachments.append(attachment)
    return attachments


def create_instance_profile(role: aws.iam.Role) -> aws.iam.InstanceProfile:
    """Create IAM instance profile."""
    return aws.iam.InstanceProfile("eb-instance-profile", role=role.name)


def create_eb_application() -> aws.elasticbeanstalk.Application:
    """Create Elastic Beanstalk application."""
    return aws.elasticbeanstalk.Application(
        "aperilex-backend-app", description="Aperilex Backend Application"
    )


def create_app_version(
    app: aws.elasticbeanstalk.Application,
    app_bucket: aws.s3.Bucket,
    source_bundle: pulumi.Input[pulumi.asset.AssetArchive],
) -> aws.elasticbeanstalk.ApplicationVersion:
    """Create Elastic Beanstalk application version."""
    backend_app_object = aws.s3.BucketObject(
        "backend-source-bundle",
        bucket=app_bucket.id,
        key="backend-source-bundle.zip",
        source=source_bundle,
    )

    return aws.elasticbeanstalk.ApplicationVersion(
        "backend-v1",
        application=app.name,
        description="Initial backend version",
        bucket=app_bucket.id,
        key=backend_app_object.key,
        opts=pulumi.ResourceOptions(depends_on=[backend_app_object]),
    )


def create_eb_environment(
    app: aws.elasticbeanstalk.Application,
    app_version: aws.elasticbeanstalk.ApplicationVersion,
    instance_profile: aws.iam.InstanceProfile,
    eb_role: aws.iam.Role,
    vpc_id: pulumi.Input[str],
    subnet_ids: list[pulumi.Input[str]],
    security_group_id: pulumi.Input[str],
    env_vars: dict[str, Any],
    db_cluster: aws.rds.Cluster,
    filings_bucket: aws.s3.Bucket,
    backend_image: docker.Image,
) -> aws.elasticbeanstalk.Environment:
    """Create Elastic Beanstalk environment."""
    solution_stack = aws.elasticbeanstalk.get_solution_stack(
        most_recent=True, name_regex="^64bit Amazon Linux 2 v.* running Docker$"
    )

    return aws.elasticbeanstalk.Environment(
        "aperilex-backend-prod-env",
        application=app.name,
        version=app_version.name,
        solution_stack_name=solution_stack.name,
        settings=[
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:autoscaling:launchconfiguration",
                name="IamInstanceProfile",
                value=instance_profile.name,
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:ec2:vpc",
                name="VPCId",
                value=vpc_id,
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:ec2:vpc",
                name="Subnets",
                value=pulumi.Output.all(*subnet_ids).apply(lambda ids: ",".join(ids)),
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:autoscaling:launchconfiguration",
                name="SecurityGroups",
                value=security_group_id,
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:elasticbeanstalk:environment",
                name="EnvironmentType",
                value="SingleInstance",
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:elasticbeanstalk:application:environment",
                name="ENVIRONMENT",
                value="production",
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:elasticbeanstalk:application:environment",
                name="EDGAR_IDENTITY",
                value=env_vars["edgar_identity"],
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:elasticbeanstalk:application:environment",
                name="OPENAI_API_KEY",
                value=env_vars["openai_api_key"],
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:elasticbeanstalk:application:environment",
                name="OPENAI_BASE_URL",
                value="https://api.openai.com/v1",
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:elasticbeanstalk:application:environment",
                name="DEFAULT_LLM_PROVIDER",
                value=env_vars["default_llm_provider"],
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:elasticbeanstalk:application:environment",
                name="LLM_MODEL",
                value=env_vars["llm_model"],
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:elasticbeanstalk:application:environment",
                name="DB_HOST",
                value=db_cluster.endpoint,
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:elasticbeanstalk:application:environment",
                name="DB_PORT",
                value=db_cluster.port.apply(str),
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:elasticbeanstalk:application:environment",
                name="DB_USER",
                value=db_cluster.master_username,
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:elasticbeanstalk:application:environment",
                name="DB_NAME",
                value=db_cluster.database_name,
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:elasticbeanstalk:application:environment",
                name="DB_PASSWORD_SECRET_ARN",
                value=db_cluster.master_user_secrets[0].secret_arn,
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:elasticbeanstalk:application:environment",
                name="AWS_S3_BUCKET",
                value=filings_bucket.id,
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:elasticbeanstalk:application:environment",
                name="AWS_REGION",
                value="us-east-2",
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:elasticbeanstalk:application:environment",
                name="ENCRYPTION_KEY",
                value=env_vars["encryption_key"],
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:elasticbeanstalk:application:environment",
                name="CORS_ALLOWED_ORIGINS",
                value='["*"]',
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:elasticbeanstalk:application:environment",
                name="IMAGE_NAME",
                value=backend_image.image_name,
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:elasticbeanstalk:environment",
                name="ServiceRole",
                value=eb_role.arn,
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:autoscaling:launchconfiguration",
                name="InstanceType",
                value="t3.micro",
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:autoscaling:asg",
                name="MinSize",
                value="1",
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:autoscaling:asg",
                name="MaxSize",
                value="1",
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:autoscaling:launchconfiguration",
                name="RootVolumeSize",
                value="8",
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:autoscaling:launchconfiguration",
                name="RootVolumeType",
                value="gp2",
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:elasticbeanstalk:environment:process:default",
                name="HealthCheckPath",
                value="/api/health",
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:elasticbeanstalk:environment:process:default",
                name="HealthCheckInterval",
                value="30",
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:elasticbeanstalk:environment:process:default",
                name="HealthCheckTimeout",
                value="3",
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:elasticbeanstalk:environment:process:default",
                name="HealthyThresholdCount",
                value="3",
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:elasticbeanstalk:environment:process:default",
                name="UnhealthyThresholdCount",
                value="10",
            ),
            aws.elasticbeanstalk.EnvironmentSettingArgs(
                namespace="aws:elasticbeanstalk:application:environment",
                name="RATE_LIMIT_REQUESTS_PER_HOUR",
                value="50",
            ),
        ],
        opts=pulumi.ResourceOptions(depends_on=[app_version, instance_profile]),
    )
