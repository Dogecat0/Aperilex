"""AWS Secrets Manager implementation for production environments."""

from __future__ import annotations

import asyncio
import base64
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import boto3
from botocore.exceptions import ClientError

from src.application.interfaces.secret import (
    ISecretManager,
    SecretMetadata,
    SecretVersion,
)
from src.shared.config.interfaces import SecretRotationConfig


class AWSSecretsManager(ISecretManager):
    """Secrets manager backed by AWS Secrets Manager."""

    def __init__(
        self,
        region_name: str,
        session: boto3.session.Session | None = None,
    ) -> None:
        if not region_name:
            raise RuntimeError("AWSSecretsManager requires an AWS region")

        self._session = session or boto3.session.Session(region_name=region_name)
        self._client = self._session.client("secretsmanager", region_name=region_name)
        self._region = region_name

    async def _call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return await asyncio.to_thread(func, *args, **kwargs)

    @staticmethod
    def _decode_secret(response: dict[str, Any]) -> str:
        if "SecretString" in response and response["SecretString"] is not None:
            return str(response["SecretString"])

        if "SecretBinary" in response and response["SecretBinary"] is not None:
            decoded = base64.b64decode(response["SecretBinary"])
            return decoded.decode("utf-8")

        raise ValueError("Secret response did not include a value")

    @staticmethod
    def _decode_secret_binary(response: dict[str, Any]) -> bytes:
        if "SecretBinary" in response and response["SecretBinary"] is not None:
            return base64.b64decode(response["SecretBinary"])

        if "SecretString" in response and response["SecretString"] is not None:
            return str(response["SecretString"]).encode("utf-8")

        raise ValueError("Secret response did not include a value")

    def _handle_client_error(self, exc: ClientError, secret_name: str) -> None:
        error_code = exc.response.get("Error", {}).get("Code", "Unknown")
        if error_code in {"ResourceNotFoundException", "DecryptionFailure"}:
            raise KeyError(f"Secret '{secret_name}' not found or inaccessible") from exc
        raise RuntimeError(
            f"AWS Secrets Manager operation failed for '{secret_name}': {error_code}"
        ) from exc

    async def get_secret(
        self,
        secret_name: str,
        version_id: str | None = None,
        version_stage: str | None = None,
    ) -> str:
        try:
            response = await self._call(
                self._client.get_secret_value,
                SecretId=secret_name,
                **{
                    k: v
                    for k, v in {
                        "VersionId": version_id,
                        "VersionStage": version_stage,
                    }.items()
                    if v is not None
                },
            )
        except ClientError as exc:  # pragma: no cover - requires AWS
            self._handle_client_error(exc, secret_name)
        return self._decode_secret(response)

    async def get_secret_binary(
        self,
        secret_name: str,
        version_id: str | None = None,
        version_stage: str | None = None,
    ) -> bytes:
        try:
            response = await self._call(
                self._client.get_secret_value,
                SecretId=secret_name,
                **{
                    k: v
                    for k, v in {
                        "VersionId": version_id,
                        "VersionStage": version_stage,
                    }.items()
                    if v is not None
                },
            )
        except ClientError as exc:  # pragma: no cover - requires AWS
            self._handle_client_error(exc, secret_name)
        return self._decode_secret_binary(response)

    async def create_secret(
        self,
        secret_name: str,
        secret_value: str | bytes,
        description: str | None = None,
        tags: dict[str, str] | None = None,
    ) -> SecretMetadata:
        params: dict[str, Any] = {"Name": secret_name}
        if isinstance(secret_value, bytes):
            params["SecretBinary"] = base64.b64encode(secret_value)
        else:
            params["SecretString"] = secret_value
        if description:
            params["Description"] = description
        if tags:
            params["Tags"] = [{"Key": k, "Value": v} for k, v in tags.items()]

        try:
            response = await self._call(self._client.create_secret, **params)
        except ClientError as exc:  # pragma: no cover - requires AWS
            self._handle_client_error(exc, secret_name)

        now = datetime.now(UTC)
        return SecretMetadata(
            schema_version=1,
            name=secret_name,
            version=response.get("VersionId"),
            created_at=now,
            updated_at=now,
            rotation_enabled=False,
            tags=tags or {},
        )

    async def update_secret(
        self,
        secret_name: str,
        secret_value: str | bytes,
        version_stage: str | None = None,
    ) -> SecretMetadata:
        params: dict[str, Any] = {"SecretId": secret_name}
        if isinstance(secret_value, bytes):
            params["SecretBinary"] = base64.b64encode(secret_value)
        else:
            params["SecretString"] = secret_value
        if version_stage:
            params["VersionStages"] = [version_stage]

        try:
            response = await self._call(self._client.put_secret_value, **params)
        except ClientError as exc:  # pragma: no cover - requires AWS
            self._handle_client_error(exc, secret_name)

        now = datetime.now(UTC)
        return SecretMetadata(
            schema_version=1,
            name=secret_name,
            version=response.get("VersionId"),
            created_at=now,
            updated_at=now,
            rotation_enabled=False,
        )

    async def delete_secret(
        self,
        secret_name: str,
        recovery_window_days: int | None = 30,
        force_delete: bool = False,
    ) -> bool:
        params: dict[str, Any] = {"SecretId": secret_name}
        if force_delete:
            params["ForceDeleteWithoutRecovery"] = True
        elif recovery_window_days is not None:
            params["RecoveryWindowInDays"] = recovery_window_days

        try:
            await self._call(self._client.delete_secret, **params)
        except ClientError as exc:  # pragma: no cover - requires AWS
            self._handle_client_error(exc, secret_name)
        return True

    async def restore_secret(self, secret_name: str) -> SecretMetadata:
        try:
            response = await self._call(
                self._client.restore_secret,
                SecretId=secret_name,
            )
        except ClientError as exc:  # pragma: no cover - requires AWS
            self._handle_client_error(exc, secret_name)

        now = datetime.now(UTC)
        return SecretMetadata(
            schema_version=1,
            name=secret_name,
            version=response.get("VersionId"),
            created_at=now,
            updated_at=now,
            rotation_enabled=False,
        )

    async def rotate_secret(
        self,
        secret_name: str,
        rotation_config: SecretRotationConfig | None = None,
    ) -> bool:
        params: dict[str, Any] = {"SecretId": secret_name}
        if rotation_config and rotation_config.rotation_lambda_arn:
            params["RotationLambdaARN"] = rotation_config.rotation_lambda_arn
        if rotation_config and rotation_config.automatically_after_days:
            params["RotateImmediately"] = False
            params["RotationRules"] = {
                "AutomaticallyAfterDays": rotation_config.automatically_after_days
            }
        else:
            params["RotateImmediately"] = True

        try:
            await self._call(self._client.rotate_secret, **params)
        except ClientError as exc:  # pragma: no cover - requires AWS
            self._handle_client_error(exc, secret_name)
        return True

    async def list_secrets(
        self,
        prefix: str | None = None,
        include_deleted: bool = False,
    ) -> list[SecretMetadata]:
        paginator = self._client.get_paginator("list_secrets")
        results: list[SecretMetadata] = []

        def _to_metadata(item: dict[str, Any]) -> SecretMetadata:
            return SecretMetadata(
                schema_version=1,
                name=item["Name"],
                version=item.get("PrimaryRegion", "v1"),
                created_at=item.get("CreatedDate", datetime.now(UTC)),
                updated_at=item.get("LastChangedDate", datetime.now(UTC)),
                rotation_enabled=item.get("RotationEnabled", False),
                rotation_period_days=item.get("RotationRules", {}).get(
                    "AutomaticallyAfterDays"
                ),
                tags={tag["Key"]: tag.get("Value", "") for tag in item.get("Tags", [])},
            )

        for page in await self._call(
            paginator.paginate,
            IncludePlannedDelete=include_deleted,
            PaginationConfig={"PageSize": 100},
        ):  # pragma: no cover - requires AWS
            for item in page.get("SecretList", []):
                name = item.get("Name", "")
                if prefix and not name.startswith(prefix):
                    continue
                results.append(_to_metadata(item))
        return results

    async def get_secret_metadata(self, secret_name: str) -> SecretMetadata:
        try:
            response = await self._call(
                self._client.describe_secret,
                SecretId=secret_name,
            )
        except ClientError as exc:  # pragma: no cover - requires AWS
            self._handle_client_error(exc, secret_name)

        created = response.get("CreatedDate", datetime.now(UTC))
        updated = response.get("LastChangedDate", created)
        return SecretMetadata(
            schema_version=1,
            name=response.get("Name", secret_name),
            version=response.get("VersionIdsToStages", {}).get("AWSCURRENT", [None])[0],
            created_at=created,
            updated_at=updated,
            rotation_enabled=response.get("RotationEnabled", False),
            rotation_period_days=response.get("RotationRules", {}).get(
                "AutomaticallyAfterDays"
            ),
            last_rotated_at=response.get("LastRotatedDate"),
            tags={tag["Key"]: tag.get("Value", "") for tag in response.get("Tags", [])},
        )

    async def list_secret_versions(
        self,
        secret_name: str,
        include_deprecated: bool = False,
    ) -> list[SecretVersion]:
        try:
            response = await self._call(
                self._client.list_secret_version_ids,
                SecretId=secret_name,
                IncludeDeprecated=include_deprecated,
            )
        except ClientError as exc:  # pragma: no cover - requires AWS
            self._handle_client_error(exc, secret_name)

        versions: list[SecretVersion] = []
        for item in response.get("Versions", []):
            staged = item.get("VersionStages", [])
            versions.append(
                SecretVersion(
                    schema_version=1,
                    version_id=item.get("VersionId", ""),
                    version_stage=staged[0] if staged else "AWSCURRENT",
                    created_at=item.get("CreatedDate", datetime.now(UTC)),
                    is_current="AWSCURRENT" in staged,
                )
            )
        return versions

    async def tag_secret(
        self,
        secret_name: str,
        tags: dict[str, str],
    ) -> bool:
        try:
            await self._call(
                self._client.tag_resource,
                SecretId=secret_name,
                Tags=[{"Key": key, "Value": value} for key, value in tags.items()],
            )
        except ClientError as exc:  # pragma: no cover - requires AWS
            self._handle_client_error(exc, secret_name)
        return True

    async def untag_secret(
        self,
        secret_name: str,
        tag_keys: list[str],
    ) -> bool:
        try:
            await self._call(
                self._client.untag_resource,
                SecretId=secret_name,
                TagKeys=tag_keys,
            )
        except ClientError as exc:  # pragma: no cover - requires AWS
            self._handle_client_error(exc, secret_name)
        return True

    async def validate_secret(
        self,
        secret_name: str,
        validator_arn: str | None = None,
    ) -> bool:
        try:
            value = await self.get_secret(secret_name)
        except KeyError:
            return False
        return bool(value)
