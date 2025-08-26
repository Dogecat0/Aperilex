"""Database infrastructure for Aperilex (RDS Aurora)."""

import pulumi
import pulumi_aws as aws


def create_db_subnet_group(
    private_subnet_ids: list[pulumi.Input[str]],
) -> aws.rds.SubnetGroup:
    """Create DB subnet group for RDS cluster."""
    return aws.rds.SubnetGroup(
        "db-subnet-group",
        subnet_ids=private_subnet_ids,
        tags={"Name": "aperilex-db-subnet-group"},
    )


def create_aurora_cluster(
    db_subnet_group_name: pulumi.Input[str], db_security_group_id: pulumi.Input[str]
) -> tuple[aws.rds.Cluster, aws.rds.ClusterInstance]:
    """Create Aurora Serverless v2 PostgreSQL cluster with instance."""
    cluster = aws.rds.Cluster(
        "aperilex-db-cluster",
        engine=aws.rds.EngineType.AURORA_POSTGRESQL,
        engine_mode="provisioned",  # Aurora Serverless v2 uses 'provisioned' engine mode
        db_subnet_group_name=db_subnet_group_name,
        vpc_security_group_ids=[db_security_group_id],
        database_name="aperilexdb",
        master_username="db_admin",
        manage_master_user_password=True,
        skip_final_snapshot=True,
        serverlessv2_scaling_configuration=aws.rds.ClusterServerlessv2ScalingConfigurationArgs(
            min_capacity=0,  # Changed from 0 to 0.5 as minimum
            max_capacity=1.0,
        ),
        tags={"Name": "aperilex-db-cluster"},
        opts=pulumi.ResourceOptions(protect=True),  # Protect from accidental deletion
    )

    # Create Aurora Serverless v2 instance
    instance = aws.rds.ClusterInstance(
        "aperilex-db-instance",
        cluster_identifier=cluster.id,
        instance_class="db.serverless",  # Required for Aurora Serverless v2
        engine=aws.rds.EngineType.AURORA_POSTGRESQL,
        tags={"Name": "aperilex-db-instance"},
        opts=pulumi.ResourceOptions(protect=True),  # Protect from accidental deletion
    )

    return cluster, instance
