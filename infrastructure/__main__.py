"""An AWS Python Pulumi program - Main orchestration file."""

import os

import pulumi
import pulumi_aws as aws
from dotenv import load_dotenv
from orchestration import (
    create_dns_records,
    export_outputs,
    setup_api_gateway,
    setup_backend,
    setup_certificate,
    setup_database,
    setup_frontend,
    setup_networking,
)

load_dotenv()

# Load and validate environment variables
edgar_identity = os.getenv("EDGAR_IDENTITY", "")
openai_api_key = os.getenv("OPENAI_API_KEY", "")
default_llm_provider = os.getenv("DEFAULT_LLM_PROVIDER", "")
llm_model = os.getenv("LLM_MODEL", "")
encryption_key = os.getenv("ENCRYPTION_KEY", "")

if not all(
    [edgar_identity, openai_api_key, default_llm_provider, llm_model, encryption_key]
):
    raise ValueError(
        "One or more required environment variables are not set. Please check your .env file in the infrastructure folder."
    )

env_vars = {
    "edgar_identity": edgar_identity,
    "openai_api_key": openai_api_key,
    "default_llm_provider": default_llm_provider,
    "llm_model": llm_model,
    "encryption_key": encryption_key,
}

# --- Setup Providers and Domain ---
us_east_1_provider = aws.Provider("us-east-1-provider", region="us-east-1")
us_east_2_provider = aws.Provider("us-east-2-provider", region="us-east-2")

zone_lookup = aws.route53.get_zone(name="aperilexlabs.com", private_zone=False)
zone_labs = aws.route53.Zone.get("aperilexlabs_zone", zone_lookup.zone_id)

aperilexlabs_domain = aws.route53domains.RegisteredDomain(
    "aperilexlabs_domain",
    admin_privacy=True,
    auto_renew=True,
    billing_privacy=True,
    domain_name="aperilexlabs.com",
    registrant_privacy=True,
    tech_privacy=True,
    transfer_lock=True,
    opts=pulumi.ResourceOptions(protect=True),
)

# --- Deploy Infrastructure ---
# 1. Certificate (shared between frontend and any future services)
domain_certificate = setup_certificate(us_east_1_provider)

# 2. Networking
networking_resources = setup_networking()

# 3. Database
db_cluster = setup_database(networking_resources)

# 4. Backend
backend_app_bucket, backend_filings_bucket, eb_env = setup_backend(
    networking_resources, db_cluster, env_vars
)

# 5. API Gateway
api = setup_api_gateway(eb_env)

# 6. Frontend (includes API routing through CloudFront)
frontend_bucket, frontend_website_config, web_distribution = setup_frontend(
    domain_certificate, api
)

# 7. DNS Records
create_dns_records(zone_labs, web_distribution)

# 8. Export Outputs
export_outputs(
    frontend_bucket,
    frontend_website_config,
    web_distribution,
    db_cluster,
    eb_env,
    backend_filings_bucket,
    api,
)
