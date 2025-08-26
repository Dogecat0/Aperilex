"""VPC and networking resources for Aperilex infrastructure."""

import pulumi
import pulumi_aws as aws


def create_vpc() -> aws.ec2.Vpc:
    """Create VPC for the application."""
    return aws.ec2.Vpc(
        "app-vpc",
        cidr_block="10.0.0.0/16",
        enable_dns_hostnames=True,
        enable_dns_support=True,
        tags={"Name": "aperilex-app-vpc"},
    )


def create_public_subnet(
    vpc_id: pulumi.Input[str], cidr_block: str, az: str, name: str
) -> aws.ec2.Subnet:
    """Create a public subnet."""
    return aws.ec2.Subnet(
        name.lower().replace(" ", "-"),
        vpc_id=vpc_id,
        cidr_block=cidr_block,
        availability_zone=az,
        map_public_ip_on_launch=True,
        tags={"Name": name},
    )


def create_private_subnet(
    vpc_id: pulumi.Input[str], cidr_block: str, az: str, name: str
) -> aws.ec2.Subnet:
    """Create a private subnet."""
    return aws.ec2.Subnet(
        name.lower().replace(" ", "-"),
        vpc_id=vpc_id,
        cidr_block=cidr_block,
        availability_zone=az,
        tags={"Name": name},
    )


def create_internet_gateway(vpc_id: pulumi.Input[str]) -> aws.ec2.InternetGateway:
    """Create Internet Gateway."""
    return aws.ec2.InternetGateway(
        "internet-gateway",
        vpc_id=vpc_id,
        tags={"Name": "aperilex-igw"},
    )


def create_public_route_table(
    vpc_id: pulumi.Input[str], gateway_id: pulumi.Input[str]
) -> aws.ec2.RouteTable:
    """Create public route table with internet gateway route."""
    return aws.ec2.RouteTable(
        "public-route-table",
        vpc_id=vpc_id,
        routes=[
            aws.ec2.RouteTableRouteArgs(cidr_block="0.0.0.0/0", gateway_id=gateway_id)
        ],
        tags={"Name": "aperilex-public-rt"},
    )


def create_private_route_table(vpc_id: pulumi.Input[str]) -> aws.ec2.RouteTable:
    """Create private route table."""
    return aws.ec2.RouteTable(
        "private-route-table",
        vpc_id=vpc_id,
        tags={"Name": "aperilex-private-rt"},
    )


def associate_subnet_with_route_table(
    subnet_id: pulumi.Input[str], route_table_id: pulumi.Input[str], name: str
) -> aws.ec2.RouteTableAssociation:
    """Associate subnet with route table."""
    return aws.ec2.RouteTableAssociation(
        name,
        subnet_id=subnet_id,
        route_table_id=route_table_id,
    )


def create_eb_security_group(vpc_id: pulumi.Input[str]) -> aws.ec2.SecurityGroup:
    """Create security group for Elastic Beanstalk environment."""
    return aws.ec2.SecurityGroup(
        "eb-app-sg",
        vpc_id=vpc_id,
        description="Security group for the Elastic Beanstalk app",
        ingress=[
            aws.ec2.SecurityGroupIngressArgs(
                from_port=80,
                to_port=80,
                protocol="tcp",
                cidr_blocks=["0.0.0.0/0"],
            )
        ],
        egress=[
            aws.ec2.SecurityGroupEgressArgs(
                protocol="-1",
                from_port=0,
                to_port=0,
                cidr_blocks=["0.0.0.0/0"],
            )
        ],
    )


def create_db_security_group(
    vpc_id: pulumi.Input[str], eb_security_group_id: pulumi.Input[str]
) -> aws.ec2.SecurityGroup:
    """Create security group for RDS database."""
    return aws.ec2.SecurityGroup(
        "db-sg",
        vpc_id=vpc_id,
        description="Allow traffic from the application to the database",
        ingress=[
            aws.ec2.SecurityGroupIngressArgs(
                protocol="tcp",
                from_port=5432,
                to_port=5432,
                security_groups=[eb_security_group_id],
            )
        ],
    )
