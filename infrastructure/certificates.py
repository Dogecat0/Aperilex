"""Certificate management for Aperilex infrastructure."""

import pulumi
import pulumi_aws as aws
import pulumi_aws.acm as acm


def create_and_validate_certificate(
    name: str,
    domain_name: str,
    provider: aws.Provider,
    subject_alternative_names: list[str] | None = None,
) -> acm.CertificateValidation:
    """Creates an ACM certificate and waits for it to be validated."""

    cert = acm.Certificate(
        f"{name}-cert",
        domain_name=domain_name,
        subject_alternative_names=subject_alternative_names,
        validation_method="DNS",
        tags={"Name": f"{domain_name}"},
        opts=pulumi.ResourceOptions(provider=provider),
    )

    # Wait for validation to complete, without creating records
    cert_validation = acm.CertificateValidation(
        f"{name}-cert-validation",
        certificate_arn=cert.arn,
        opts=pulumi.ResourceOptions(provider=provider),
    )

    return cert_validation


def create_domain_certificate(
    us_east_1_provider: aws.Provider,
) -> acm.CertificateValidation:
    """Create ACM certificate for the domain (must be in us-east-1 for CloudFront)."""
    return create_and_validate_certificate(
        name="aperilexlabs-domain",
        domain_name="aperilexlabs.com",
        subject_alternative_names=["*.aperilexlabs.com"],
        provider=us_east_1_provider,
    )
