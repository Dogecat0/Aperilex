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
    EnvironmentType,
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


def parse_environment(env_str: str | None = None) -> EnvironmentType:
    """Parse environment from string or detect automatically."""
    if env_str:
        try:
            return EnvironmentType(env_str.lower())
        except ValueError as exc:
            raise ValueError(f"Invalid environment: {env_str}") from exc

    # Auto-detect from settings
    settings = Settings()
    env_name = settings.messaging_environment.lower()

    if env_name == "production":
        return EnvironmentType.PRODUCTION
    elif env_name == "testing":
        return EnvironmentType.TESTING
    else:
        return EnvironmentType.DEVELOPMENT


def get_messaging_config(environment: EnvironmentType) -> dict[str, Any]:
    """Get messaging configuration for the environment."""
    settings = Settings()

    config = {}

    if environment == EnvironmentType.DEVELOPMENT:
        config["rabbitmq_url"] = settings.rabbitmq_url

    elif environment == EnvironmentType.PRODUCTION:
        config.update(
            {
                "aws_region": settings.aws_region,
                "aws_access_key_id": settings.aws_access_key_id,
                "aws_secret_access_key": settings.aws_secret_access_key,
                "queue_prefix": "aperilex",
                "function_prefix": "aperilex",
                "s3_bucket_name": settings.aws_s3_bucket or "aperilex-cache",
            }
        )

    return config


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
async def worker_context(
    environment: EnvironmentType, config: dict[str, Any]
) -> AsyncGenerator[None, Any]:
    """Context manager for worker lifecycle."""
    max_retries = 5
    retry_delay = 2

    try:
        for attempt in range(max_retries):
            try:
                # Initialize messaging services
                logging.info(
                    f"Initializing messaging services for {environment.value} (attempt {attempt + 1}/{max_retries})"
                )
                await initialize_services(environment, **config)

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
        environment: EnvironmentType | None = None,
    ):
        self.worker_id = worker_id or f"worker-{os.getpid()}"
        self.queues = queues or ["default", "analysis_queue", "filing_queue"]
        self.environment = environment or parse_environment()
        self.config = get_messaging_config(self.environment)
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
        logging.info(f"Environment: {self.environment.value}")
        logging.info(f"Queues: {', '.join(self.queues)}")

        if self.environment == EnvironmentType.PRODUCTION:
            logging.warning(
                "Production environment detected. "
                "In production, workers should be AWS Lambda functions, "
                "not standalone processes. This script is intended for development."
            )

        async with worker_context(self.environment, self.config):
            worker_service = await get_worker_service()

            if self.environment == EnvironmentType.DEVELOPMENT:
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

            elif self.environment == EnvironmentType.TESTING:
                # For testing, just validate setup
                logging.info("Testing environment - worker setup validated")
                health = await worker_service.health_check()
                logging.info(f"Worker health check: {health}")

            else:
                # Production - shouldn't run this script
                logging.error(
                    "This worker script should not be used in production. "
                    "Use AWS Lambda functions instead."
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
    environment = EnvironmentType(args.environment) if args.environment else None

    # Create and run worker
    worker = WorkerProcess(
        worker_id=args.worker_id,
        queues=queues,
        environment=environment,
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
