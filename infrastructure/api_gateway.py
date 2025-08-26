"""API Gateway infrastructure for Aperilex."""

import pulumi
import pulumi_aws.apigatewayv2 as apigatewayv2


def create_http_api() -> apigatewayv2.Api:
    """Create HTTP API Gateway for the backend with CORS configuration."""
    return apigatewayv2.Api(
        "aperilex-http-api",
        protocol_type="HTTP",
        description="HTTP API for Aperilex backend",
        cors_configuration=apigatewayv2.ApiCorsConfigurationArgs(
            allow_origins=["*"],
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type", "X-Request-ID", "Authorization"],
            expose_headers=["X-Request-ID"],
            max_age=86400,
        ),
    )


def create_api_integration(
    api: apigatewayv2.Api, backend_cname: pulumi.Input[str]
) -> apigatewayv2.Integration:
    """Create API integration with Elastic Beanstalk environment.

    Sets X-Forwarded headers to ensure the backend knows it's
    behind HTTPS proxies. This prevents mixed content errors
    when the backend generates redirects.
    """
    return apigatewayv2.Integration(
        "api-integration",
        api_id=api.id,
        integration_type="HTTP_PROXY",
        integration_uri=pulumi.Output.concat("http://", backend_cname, r"/{proxy}"),
        integration_method="ANY",
        payload_format_version="1.0",
        request_parameters={
            "overwrite:path": "$request.path",
        },
    )


def create_api_route(
    api: apigatewayv2.Api, integration: apigatewayv2.Integration
) -> apigatewayv2.Route:
    """Create default route that proxies all requests to the integration."""
    return apigatewayv2.Route(
        "api-default-route",
        api_id=api.id,
        route_key="ANY /{proxy+}",
        target=pulumi.Output.concat("integrations/", integration.id),
    )


def create_api_stage(
    api: apigatewayv2.Api, route: apigatewayv2.Route
) -> apigatewayv2.Stage:
    """Create stage and enable auto-deployment."""
    return apigatewayv2.Stage(
        "api-default-stage",
        api_id=api.id,
        name="$default",
        auto_deploy=True,
        opts=pulumi.ResourceOptions(depends_on=[route]),
    )
