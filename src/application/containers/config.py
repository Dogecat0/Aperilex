"""
Configuration container for managing application configuration and secrets.
"""

from dependency_injector import containers, providers

from src.application.interfaces.config import IConfigProvider
from src.application.interfaces.secret import ISecretManager


class ConfigurationContainer(containers.DeclarativeContainer):
    """Container for configuration and secret management."""

    # Configuration settings (can be overridden with env vars or config files)
    config = providers.Configuration()

    # Environment provider for environment-specific settings
    environment = providers.Object("development")

    # Config provider implementation (will be determined based on environment)
    config_provider = providers.AbstractSingleton(IConfigProvider)

    # Secret manager implementation (will be determined based on environment)
    secret_manager = providers.AbstractSingleton(ISecretManager)
