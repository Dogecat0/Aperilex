#!/usr/bin/env python3
"""
Aperilex Background Worker Process

This script runs the messaging worker process that processes tasks from the queue.
It automatically detects the environment and uses appropriate services:
- Development: RabbitMQ + LocalWorkerService
- Production: AWS SQS + Lambda (this script not used)
- Testing: Mock services

Usage:
    python scripts/run_worker.py [options]

Options:
    --worker-id ID          Set worker ID (default: auto-generated)
    --queues Q1,Q2,Q3      Comma-separated list of queues to process
    --log-level LEVEL      Logging level (default: INFO)
    --environment ENV      Force environment (development/testing/production)
"""

import asyncio
import logging
import os
import signal
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.infrastructure.messaging.factory import (  # noqa: E402
    cleanup_services,
    get_worker_service,
    initialize_services,
)
from src.shared.config.settings import Settings  # noqa: E402


def setup_logging(log_level: str = "INFO") -> None:
    """Configure logging for the worker process."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            # Add file handler in production
            # logging.FileHandler("worker.log"),
        ],
    )


def get_worker_settings(env_override: str | None = None) -> Settings:
    """Get settings for worker with optional environment override."""
    if env_override:
        import os

        # Temporarily override environment for this settings instance
        old_env = os.environ.get("ENVIRONMENT")
        os.environ["ENVIRONMENT"] = env_override
        try:
            settings = Settings()
        finally:
            # Restore original environment
            if old_env is not None:
                os.environ["ENVIRONMENT"] = old_env
            elif "ENVIRONMENT" in os.environ:
                del os.environ["ENVIRONMENT"]
    else:
        settings = Settings()

    return settings


async def import_all_tasks() -> None:
    """Import all task modules to register tasks with the worker service."""
    # Import task modules to trigger @task decorator registration
    try:
        # Analysis tasks
        from src.infrastructure.tasks import analysis_tasks

        logging.info(f"Imported analysis tasks from {analysis_tasks.__file__}")

        logging.info("All task modules imported successfully")

    except ImportError as e:
        logging.error(f"Failed to import task modules: {e}")
        raise


@asynccontextmanager
async def worker_context(settings: Settings) -> AsyncGenerator[None, Any]:
    """Context manager for worker lifecycle."""
    max_retries = 5
    retry_delay = 2

    try:
        for attempt in range(max_retries):
            try:
                # Initialize messaging services
                logging.info(
                    f"Initializing messaging services (Queue: {settings.queue_service_type}, Storage: {settings.storage_service_type}, Worker: {settings.worker_service_type}) (attempt {attempt + 1}/{max_retries})"
                )
                await initialize_services(settings)

                # Import tasks to register them
                await import_all_tasks()

                yield
                return

            except Exception as e:
                if attempt == max_retries - 1:
                    logging.error(
                        f"Failed to initialize worker after {max_retries} attempts: {e}"
                    )
                    raise

                logging.warning(
                    f"Initialization attempt {attempt + 1} failed: {e}. Retrying in {retry_delay} seconds..."
                )
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
    finally:
        # Cleanup services
        logging.info("Cleaning up messaging services")
        await cleanup_services()


class WorkerProcess:
    """Main worker process class."""

    def __init__(
        self,
        worker_id: str | None = None,
        queues: list[str] | None = None,
        settings: Settings | None = None,
    ):
        self.worker_id = worker_id or f"worker-{os.getpid()}"
        self.queues = queues or ["default", "analysis_queue", "filing_queue"]
        self.settings = settings or Settings()
        self.running = False
        self._shutdown_event = asyncio.Event()

        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals."""
        logging.info(f"Received signal {signum}, shutting down gracefully...")
        self._shutdown_event.set()

    async def run(self) -> None:
        """Run the worker process."""
        logging.info(f"Starting worker {self.worker_id}")
        logging.info(
            f"Service types - Queue: {self.settings.queue_service_type}, Storage: {self.settings.storage_service_type}, Worker: {self.settings.worker_service_type}"
        )
        logging.info(f"Queues: {', '.join(self.queues)}")

        # Warn about production usage
        if self.settings.worker_service_type == "lambda":
            logging.warning(
                "Lambda worker service type detected. "
                "In production, workers should be AWS Lambda functions, "
                "not standalone processes. This script is intended for development."
            )

        async with worker_context(self.settings):
            worker_service = await get_worker_service()

            if self.settings.worker_service_type == "local":
                # For development, start the local worker
                self.running = True

                # Start worker with specified queues
                await worker_service.start(
                    queues=self.queues,
                )

                logging.info(f"Worker {self.worker_id} started successfully")

                # Wait for shutdown signal
                await self._shutdown_event.wait()

                logging.info("Stopping worker...")
                await worker_service.stop()

            elif self.settings.worker_service_type == "mock":
                # For testing, just validate setup
                logging.info("Mock worker service - setup validated")
                health = await worker_service.health_check()
                logging.info(f"Worker health check: {health}")

            else:
                # Lambda or other - shouldn't run this script
                logging.error(
                    f"Worker service type '{self.settings.worker_service_type}' should not use this script. "
                    "Use appropriate deployment method instead."
                )
                sys.exit(1)


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Aperilex Background Worker Process",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--worker-id",
        type=str,
        help="Worker ID (default: auto-generated)",
    )

    parser.add_argument(
        "--queues",
        type=str,
        default="default,analysis_queue,filing_queue",
        help="Comma-separated list of queues to process",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    parser.add_argument(
        "--environment",
        type=str,
        choices=["development", "testing", "production"],
        help="Force environment (default: auto-detect)",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)

    # Parse arguments
    queues = [q.strip() for q in args.queues.split(",") if q.strip()]

    # Get settings with optional environment override
    settings = get_worker_settings(args.environment)

    # Create and run worker
    worker = WorkerProcess(
        worker_id=args.worker_id,
        queues=queues,
        settings=settings,
    )

    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        logging.info("Worker interrupted by user")
    except Exception as e:
        logging.error(f"Worker failed: {e}")
        sys.exit(1)

    logging.info("Worker process completed")


if __name__ == "__main__":
    main()
