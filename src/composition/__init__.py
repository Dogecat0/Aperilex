"""
Composition root for dependency injection wiring.

This module is responsible for wiring concrete implementations to abstract interfaces.
It serves as the composition root following clean architecture principles.
"""

from .container import CompositionRoot, CompositionRootInstance
from .infrastructure_wiring import InfrastructureWiring
from .provider_factory import ProviderFactory

__all__ = [
    "CompositionRoot",
    "CompositionRootInstance",
    "InfrastructureWiring",
    "ProviderFactory",
]
