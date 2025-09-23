"""
Main entry point that uses the composition root for dependency injection.

This module demonstrates how to properly initialize the application
using the composition root pattern with clean architecture.
"""

import asyncio
import logging
from importlib import import_module
from pathlib import Path
from types import ModuleType

from src.composition import CompositionRoot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """
    Main application entry point.

    This function:
    1. Initializes the composition root
    2. Wires all concrete implementations
    3. Gets the application container
    4. Runs the application
    """
    # Determine environment from environment variable or default to development
    import os

    environment = os.getenv("ENVIRONMENT", "development")

    logger.info(f"Starting Aperilex in {environment} mode")

    # Initialize composition root with all concrete implementations
    composition_root = CompositionRoot.initialize(environment)

    # Get application container with all dependencies wired
    app_container = composition_root.get_application_container()

    # Wire modules that need dependency injection
    modules_to_wire = [
        "src.presentation.api.dependencies",
        "src.presentation.api.routers.analyses",
        "src.presentation.api.routers.company",
        "src.presentation.api.routers.filing",
        "src.presentation.api.routers.tasks",
        "src.application.commands",
        "src.application.queries",
    ]

    # Filter out modules that don't exist yet
    module_objects: list[ModuleType] = []
    for module_path in modules_to_wire:
        module_file = Path("src", *module_path.split(".")[1:]).with_suffix(".py")
        if module_file.exists():
            module_objects.append(import_module(module_path))

    if module_objects:
        composition_root.wire_modules(module_objects)
        logger.info(f"Wired {len(module_objects)} modules")

    # Get CQRS dispatcher with all handlers registered from app container
    cqrs_container = app_container.cqrs()
    _ = cqrs_container.dispatcher()
    handler_registrar = cqrs_container.handler_registrar()

    # Register all CQRS handlers
    try:
        handler_registrar.register_all_handlers()
        logger.info("Registered all CQRS handlers")
    except ImportError as e:
        logger.warning(f"Some handlers not yet implemented: {e}")

    # Get provider instances for demonstration from app container
    providers = app_container.providers_container()

    # Log provider types being used
    logger.info(f"Storage Provider: {providers.storage_provider_type()}")
    logger.info(f"Queue Provider: {providers.queue_provider_type()}")
    logger.info(f"Worker Provider: {providers.worker_provider_type()}")
    logger.info(f"LLM Provider: {providers.llm_provider_type()}")
    logger.info(f"Data Source Provider: {providers.data_source_provider_type()}")
    logger.info(f"Database Provider: {providers.database_provider_type()}")

    logger.info("Application initialized successfully with clean architecture")

    # Application bootstrap completes here; dedicated entry points start API servers or workers.


if __name__ == "__main__":
    asyncio.run(main())
