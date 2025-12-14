"""Offline unit tests for AWSSecretsManager."""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError

from src.infrastructure.secret.aws_secrets_manager import AWSSecretsManager
from src.shared.config.interfaces import SecretRotationConfig


def _client_error(code: str) -> ClientError:
    return ClientError(
        {"Error": {"Code": code, "Message": "boom"}},
        "GetSecretValue",
    )


def _make_manager(client: Mock) -> AWSSecretsManager:
    session = Mock()
    session.client.return_value = client
    return AWSSecretsManager(region_name="us-east-1", session=session)


def test_requires_region() -> None:
    with pytest.raises(RuntimeError, match="requires an AWS region"):
        AWSSecretsManager(region_name="")


def test_decode_secret_prefers_string() -> None:
    assert (
        AWSSecretsManager._decode_secret(
            {
                "SecretString": "value",
                "SecretBinary": base64.b64encode(b"ignored"),
            }
        )
        == "value"
    )


def test_decode_secret_decodes_binary() -> None:
    encoded = base64.b64encode(b"hello")
    assert AWSSecretsManager._decode_secret({"SecretBinary": encoded}) == "hello"


def test_decode_secret_raises_when_missing_value() -> None:
    with pytest.raises(ValueError, match="did not include a value"):
        AWSSecretsManager._decode_secret({})


def test_decode_secret_binary_prefers_binary() -> None:
    encoded = base64.b64encode(b"raw")
    assert (
        AWSSecretsManager._decode_secret_binary(
            {
                "SecretBinary": encoded,
                "SecretString": "ignored",
            }
        )
        == b"raw"
    )


def test_decode_secret_binary_encodes_string() -> None:
    assert AWSSecretsManager._decode_secret_binary({"SecretString": "value"}) == b"value"


def test_decode_secret_binary_raises_when_missing_value() -> None:
    with pytest.raises(ValueError, match="did not include a value"):
        AWSSecretsManager._decode_secret_binary({})


@pytest.mark.asyncio
async def test_get_secret_passes_version_args() -> None:
    client = Mock()
    client.get_secret_value.return_value = {"SecretString": "ok"}
    manager = _make_manager(client)

    assert (
        await manager.get_secret(
            "TEST_SECRET",
            version_id="version-1",
            version_stage="AWSCURRENT",
        )
        == "ok"
    )
    client.get_secret_value.assert_called_once_with(
        SecretId="TEST_SECRET",
        VersionId="version-1",
        VersionStage="AWSCURRENT",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "code",
    ["ResourceNotFoundException", "DecryptionFailure"],
)
async def test_get_secret_maps_missing_secrets_to_key_error(code: str) -> None:
    client = Mock()
    client.get_secret_value.side_effect = _client_error(code)
    manager = _make_manager(client)

    with pytest.raises(KeyError) as excinfo:
        await manager.get_secret("MISSING_SECRET")
    assert excinfo.value.args[0] == "Secret 'MISSING_SECRET' not found or inaccessible"


@pytest.mark.asyncio
async def test_get_secret_maps_other_errors_to_runtime_error() -> None:
    client = Mock()
    client.get_secret_value.side_effect = _client_error("InternalServiceErrorException")
    manager = _make_manager(client)

    with pytest.raises(
        RuntimeError,
        match="AWS Secrets Manager operation failed for 'BAD_SECRET': InternalServiceErrorException",
    ):
        await manager.get_secret("BAD_SECRET")


@pytest.mark.asyncio
async def test_get_secret_binary_decodes_string_values() -> None:
    client = Mock()
    client.get_secret_value.return_value = {"SecretString": "value"}
    manager = _make_manager(client)

    assert await manager.get_secret_binary("TEST_SECRET") == b"value"


@pytest.mark.asyncio
async def test_get_secret_binary_decodes_binary_values() -> None:
    client = Mock()
    client.get_secret_value.return_value = {"SecretBinary": base64.b64encode(b"binary")}
    manager = _make_manager(client)

    assert await manager.get_secret_binary("TEST_SECRET") == b"binary"


@pytest.mark.asyncio
async def test_create_secret_passes_binary_and_tags() -> None:
    client = Mock()
    client.create_secret.return_value = {"VersionId": "v1"}
    manager = _make_manager(client)

    created = await manager.create_secret(
        "BINARY_SECRET",
        b"raw",
        description="test",
        tags={"env": "local"},
    )

    assert created.name == "BINARY_SECRET"
    assert created.version == "v1"
    assert created.tags == {"env": "local"}

    client.create_secret.assert_called_once()
    _, kwargs = client.create_secret.call_args
    assert kwargs["Name"] == "BINARY_SECRET"
    assert kwargs["SecretBinary"] == b"raw"
    assert kwargs["Description"] == "test"
    assert kwargs["Tags"] == [{"Key": "env", "Value": "local"}]


@pytest.mark.asyncio
async def test_create_secret_passes_string_value() -> None:
    client = Mock()
    client.create_secret.return_value = {"VersionId": "v1"}
    manager = _make_manager(client)

    created = await manager.create_secret("STRING_SECRET", "value")

    assert created.name == "STRING_SECRET"
    assert created.tags == {}
    client.create_secret.assert_called_once_with(Name="STRING_SECRET", SecretString="value")


@pytest.mark.asyncio
async def test_update_secret_sets_version_stage() -> None:
    client = Mock()
    client.put_secret_value.return_value = {"VersionId": "v2"}
    manager = _make_manager(client)

    updated = await manager.update_secret(
        "TEST_SECRET",
        "rotated",
        version_stage="AWSPREVIOUS",
    )
    assert updated.version == "v2"
    client.put_secret_value.assert_called_once_with(
        SecretId="TEST_SECRET",
        SecretString="rotated",
        VersionStages=["AWSPREVIOUS"],
    )


@pytest.mark.asyncio
async def test_update_secret_passes_binary_values() -> None:
    client = Mock()
    client.put_secret_value.return_value = {"VersionId": "v2"}
    manager = _make_manager(client)

    updated = await manager.update_secret("TEST_SECRET", b"raw")
    assert updated.version == "v2"
    client.put_secret_value.assert_called_once_with(
        SecretId="TEST_SECRET",
        SecretBinary=b"raw",
    )


@pytest.mark.asyncio
async def test_rotate_secret_rotates_immediately_without_config() -> None:
    client = Mock()
    client.rotate_secret.return_value = {}
    manager = _make_manager(client)

    assert await manager.rotate_secret("TEST_SECRET") is True
    client.rotate_secret.assert_called_once_with(
        SecretId="TEST_SECRET",
        RotateImmediately=True,
    )


@pytest.mark.asyncio
async def test_rotate_secret_uses_rotation_rules_when_configured() -> None:
    client = Mock()
    client.rotate_secret.return_value = {}
    manager = _make_manager(client)

    config = SecretRotationConfig(
        rotation_lambda_arn="arn:aws:lambda:us-east-1:123456789012:function:rotate",
        automatically_after_days=7,
    )

    assert await manager.rotate_secret("TEST_SECRET", rotation_config=config) is True
    client.rotate_secret.assert_called_once_with(
        SecretId="TEST_SECRET",
        RotationLambdaARN=config.rotation_lambda_arn,
        RotateImmediately=False,
        RotationRules={"AutomaticallyAfterDays": 7},
    )


@pytest.mark.asyncio
async def test_get_secret_binary_passes_version_args() -> None:
    client = Mock()
    client.get_secret_value.return_value = {"SecretBinary": base64.b64encode(b"ok")}
    manager = _make_manager(client)

    assert (
        await manager.get_secret_binary(
            "TEST_SECRET",
            version_id="version-1",
            version_stage="AWSCURRENT",
        )
        == b"ok"
    )
    client.get_secret_value.assert_called_once_with(
        SecretId="TEST_SECRET",
        VersionId="version-1",
        VersionStage="AWSCURRENT",
    )


@pytest.mark.asyncio
async def test_delete_secret_defaults_to_recovery_window() -> None:
    client = Mock()
    client.delete_secret.return_value = {}
    manager = _make_manager(client)

    assert await manager.delete_secret("TEST_SECRET") is True
    client.delete_secret.assert_called_once_with(
        SecretId="TEST_SECRET",
        RecoveryWindowInDays=30,
    )


@pytest.mark.asyncio
async def test_delete_secret_supports_force_delete() -> None:
    client = Mock()
    client.delete_secret.return_value = {}
    manager = _make_manager(client)

    assert await manager.delete_secret("TEST_SECRET", force_delete=True) is True
    client.delete_secret.assert_called_once_with(
        SecretId="TEST_SECRET",
        ForceDeleteWithoutRecovery=True,
    )


@pytest.mark.asyncio
async def test_delete_secret_supports_none_recovery_window() -> None:
    client = Mock()
    client.delete_secret.return_value = {}
    manager = _make_manager(client)

    assert await manager.delete_secret("TEST_SECRET", recovery_window_days=None) is True
    client.delete_secret.assert_called_once_with(SecretId="TEST_SECRET")


@pytest.mark.asyncio
async def test_restore_secret_returns_metadata() -> None:
    client = Mock()
    client.restore_secret.return_value = {"VersionId": "v1"}
    manager = _make_manager(client)

    restored = await manager.restore_secret("TEST_SECRET")
    assert restored.name == "TEST_SECRET"
    assert restored.version == "v1"
    client.restore_secret.assert_called_once_with(SecretId="TEST_SECRET")


@pytest.mark.asyncio
async def test_list_secrets_filters_by_prefix_and_maps_metadata() -> None:
    created = datetime(2024, 1, 1, tzinfo=UTC)
    updated = datetime(2024, 1, 2, tzinfo=UTC)

    paginator = Mock()
    paginator.paginate.return_value = [
        {
            "SecretList": [
                {
                    "Name": "prod/ONE",
                    "PrimaryRegion": "v1",
                    "CreatedDate": created,
                    "LastChangedDate": updated,
                    "RotationEnabled": True,
                    "RotationRules": {"AutomaticallyAfterDays": 14},
                    "Tags": [{"Key": "env", "Value": "prod"}],
                },
                {"Name": "dev/TWO"},
            ]
        }
    ]

    client = Mock()
    client.get_paginator.return_value = paginator
    manager = _make_manager(client)

    secrets = await manager.list_secrets(prefix="prod/", include_deleted=True)
    assert [secret.name for secret in secrets] == ["prod/ONE"]
    assert secrets[0].rotation_enabled is True
    assert secrets[0].rotation_period_days == 14
    assert secrets[0].tags == {"env": "prod"}

    paginator.paginate.assert_called_once_with(
        IncludePlannedDelete=True,
        PaginationConfig={"PageSize": 100},
    )


@pytest.mark.asyncio
async def test_get_secret_metadata_maps_fields() -> None:
    created = datetime(2024, 3, 1, tzinfo=UTC)
    updated = datetime(2024, 3, 2, tzinfo=UTC)
    rotated = datetime(2024, 3, 3, tzinfo=UTC)

    client = Mock()
    client.describe_secret.return_value = {
        "Name": "TEST_SECRET",
        "CreatedDate": created,
        "LastChangedDate": updated,
        "VersionIdsToStages": {"v1": ["AWSPREVIOUS"], "v2": ["AWSCURRENT"]},
        "RotationEnabled": True,
        "RotationRules": {"AutomaticallyAfterDays": 30},
        "LastRotatedDate": rotated,
        "Tags": [{"Key": "team", "Value": "platform"}],
    }
    manager = _make_manager(client)

    metadata = await manager.get_secret_metadata("IGNORED_NAME")
    assert metadata.name == "TEST_SECRET"
    assert metadata.version == "v2"
    assert metadata.created_at == created
    assert metadata.updated_at == updated
    assert metadata.rotation_enabled is True
    assert metadata.rotation_period_days == 30
    assert metadata.last_rotated_at == rotated
    assert metadata.tags == {"team": "platform"}
    client.describe_secret.assert_called_once_with(SecretId="IGNORED_NAME")


@pytest.mark.asyncio
async def test_list_secret_versions_maps_stages() -> None:
    created = datetime(2024, 5, 1, tzinfo=UTC)
    current = datetime(2024, 5, 2, tzinfo=UTC)

    client = Mock()
    client.list_secret_version_ids.return_value = {
        "Versions": [
            {
                "VersionId": "v1",
                "VersionStages": ["AWSPREVIOUS"],
                "CreatedDate": created,
            },
            {
                "VersionId": "v2",
                "VersionStages": ["AWSCURRENT"],
                "CreatedDate": current,
            },
            {
                "VersionId": "v3",
                "VersionStages": [],
                "CreatedDate": current,
            },
        ]
    }
    manager = _make_manager(client)

    versions = await manager.list_secret_versions("TEST_SECRET", include_deprecated=True)
    assert [v.version_id for v in versions] == ["v1", "v2", "v3"]
    assert versions[0].version_stage == "AWSPREVIOUS"
    assert versions[0].is_current is False
    assert versions[1].version_stage == "AWSCURRENT"
    assert versions[1].is_current is True
    assert versions[2].version_stage == "AWSCURRENT"
    assert versions[2].is_current is False

    client.list_secret_version_ids.assert_called_once_with(
        SecretId="TEST_SECRET",
        IncludeDeprecated=True,
    )


@pytest.mark.asyncio
async def test_tag_secret_sends_tags() -> None:
    client = Mock()
    client.tag_resource.return_value = {}
    manager = _make_manager(client)

    assert await manager.tag_secret("TEST_SECRET", {"env": "local"}) is True
    client.tag_resource.assert_called_once_with(
        SecretId="TEST_SECRET",
        Tags=[{"Key": "env", "Value": "local"}],
    )


@pytest.mark.asyncio
async def test_untag_secret_sends_tag_keys() -> None:
    client = Mock()
    client.untag_resource.return_value = {}
    manager = _make_manager(client)

    assert await manager.untag_secret("TEST_SECRET", ["env", "team"]) is True
    client.untag_resource.assert_called_once_with(
        SecretId="TEST_SECRET",
        TagKeys=["env", "team"],
    )


@pytest.mark.asyncio
async def test_validate_secret_returns_false_when_missing() -> None:
    client = Mock()
    manager = _make_manager(client)
    client.get_secret_value.side_effect = _client_error("ResourceNotFoundException")

    assert await manager.validate_secret("MISSING_SECRET") is False


@pytest.mark.asyncio
async def test_validate_secret_returns_truthiness_of_value() -> None:
    client = Mock()
    manager = _make_manager(client)
    client.get_secret_value.return_value = {"SecretString": ""}

    assert await manager.validate_secret("EMPTY_SECRET") is False

    client.get_secret_value.return_value = {"SecretString": "value"}
    assert await manager.validate_secret("NON_EMPTY_SECRET") is True
