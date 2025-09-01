#!/usr/bin/env python
"""
Simplified AWS Migration Script for Aperilex
Designed for 2-step migration: Local Export → Beanstalk Import

Usage:
  Step 1 (Local): python migrate_to_aws_simplified.py --export
  Step 2 (Beanstalk): python migrate_to_aws_simplified.py --import --dump-key migrations/aperilex_db_TIMESTAMP.sql
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import boto3
import psycopg2
import sqlparse
from dotenv import load_dotenv
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class SimplifiedAWSMigration:
    """Simplified migration handler for 2-step process"""

    def __init__(self, dump_s3_key: str = None):
        """Initialize migration handler"""
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.dump_s3_key = dump_s3_key

        # Detect environment
        self.is_beanstalk = os.path.exists("/var/app/current")

        # AWS clients
        self.s3_client = None
        self.rds_client = None

        # Connection pool for Aurora
        self._connection_pool = None

        # Simplified configuration
        self.config = {
            "data_path": (
                Path("/var/app/current/data") if self.is_beanstalk else Path("./data")
            ),
            "temp_path": Path("/tmp") if self.is_beanstalk else Path("./backups"),
            "s3_bucket": os.getenv("AWS_S3_BUCKET"),
            "aurora_endpoint": os.getenv("DB_HOST"),
            "aurora_database": os.getenv("DB_NAME", "aperilexdb"),
            "aurora_username": os.getenv("DB_USER", "db_admin"),
            "aurora_secret_arn": os.getenv("DB_PASSWORD_SECRET_ARN"),
            "region": os.getenv("AWS_REGION", "us-east-2"),
        }

        logger.info(f"Environment: {'Beanstalk' if self.is_beanstalk else 'Local'}")
        logger.info(f"Timestamp: {self.timestamp}")

    def setup_aws_clients(self):
        """Initialize AWS service clients"""
        session = boto3.Session(region_name=self.config["region"])
        self.s3_client = session.client("s3")
        self.rds_client = session.client("rds")
        self.secrets_client = session.client("secretsmanager")
        logger.info(f"AWS clients initialized for region: {self.config['region']}")

    def find_s3_bucket(self):
        """Find the S3 bucket (handles dynamic suffixes)"""
        if self.config["s3_bucket"]:
            return True

        # List buckets and find the one matching our pattern
        response = self.s3_client.list_buckets()
        for bucket in response.get("Buckets", []):
            if bucket["Name"].startswith("aperilex-backend-filings-bucket"):
                self.config["s3_bucket"] = bucket["Name"]
                logger.info(f"Found S3 bucket: {bucket['Name']}")
                return True

        logger.error("S3 bucket not found")
        return False

    def get_aurora_password(self) -> str:
        """Get Aurora password from Secrets Manager (Beanstalk) or environment (Local)"""
        # For local environment, use environment variable
        if not self.is_beanstalk:
            password = os.getenv("AURORA_PASSWORD")
            if password:
                return password
            logger.error("Set AURORA_PASSWORD environment variable for local migration")
            sys.exit(1)

        # For Beanstalk, use Secrets Manager
        if not self.config["aurora_secret_arn"]:
            logger.error("DB_PASSWORD_SECRET_ARN not found in environment")
            sys.exit(1)

        try:
            response = self.secrets_client.get_secret_value(
                SecretId=self.config["aurora_secret_arn"]
            )
            secret_data = json.loads(response["SecretString"])
            return secret_data.get("password")
        except Exception as e:
            logger.error(f"Failed to retrieve password from Secrets Manager: {e}")
            sys.exit(1)

    def export_and_upload(self) -> bool:
        """Export local database and upload to S3 (LOCAL EXECUTION ONLY)"""
        if self.is_beanstalk:
            logger.error("Export must be run from LOCAL environment, not Beanstalk")
            return False

        # Ensure temp directory exists
        backup_dir = self.config["temp_path"] / f"migration_{self.timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        dump_file = backup_dir / f"aperilex_db_{self.timestamp}.sql"

        # Step 1: Export from Docker container
        logger.info("Exporting database from local Docker container...")
        try:
            cmd = [
                "docker",
                "exec",
                "aperilex-postgres-1",
                "pg_dump",
                "-U",
                "aperilex",
                "-d",
                "aperilex",
                "--no-owner",
                "--no-acl",
                "--clean",
                "--if-exists",
            ]

            with open(dump_file, "w") as f:
                subprocess.run(
                    cmd, stdout=f, stderr=subprocess.PIPE, text=True, check=True
                )

            file_size_mb = dump_file.stat().st_size / 1024 / 1024
            logger.info(f"✓ Database exported: {file_size_mb:.2f} MB")

        except subprocess.CalledProcessError as e:
            logger.error(f"Database export failed: {e.stderr}")
            return False

        # Step 2: Upload to S3
        s3_key = f"migrations/aperilex_db_{self.timestamp}.sql"
        logger.info(f"Uploading to S3: s3://{self.config['s3_bucket']}/{s3_key}")

        try:
            self.s3_client.upload_file(str(dump_file), self.config["s3_bucket"], s3_key)
            logger.info("✓ Uploaded to S3")
            logger.info(f"\n{'=' * 60}")
            logger.info("NEXT STEPS:")
            logger.info("1. SSH/SSM into Beanstalk instance:")
            logger.info(
                "   aws ssm start-session --target i-083b20fbd26a450e9 --region us-east-2"
            )
            logger.info("2. Run import command:")
            logger.info("   cd /var/app/current")
            logger.info(
                f"   python scripts/migrate_to_aws_simplified.py --import --dump-key {s3_key}"
            )
            logger.info(f"{'=' * 60}")

        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            return False

        # Step 3: Sync files to S3
        logger.info("\nSyncing local files to S3...")
        for dir_name in ["filings", "analyses"]:
            local_dir = self.config["data_path"] / dir_name
            if not local_dir.exists():
                logger.warning(f"Directory not found: {local_dir}")
                continue

            cmd = [
                "aws",
                "s3",
                "sync",
                str(local_dir),
                f"s3://{self.config['s3_bucket']}/{dir_name}/",
                "--region",
                self.config["region"],
                "--exclude",
                "*.pyc",
                "--exclude",
                "__pycache__/*",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"✓ Synced {dir_name}/ to S3")
            else:
                logger.error(f"Failed to sync {dir_name}: {result.stderr}")

        return True

    def download_and_import(self) -> bool:
        """Download dump from S3 and import to Aurora (BEANSTALK EXECUTION ONLY)"""
        if not self.is_beanstalk:
            logger.warning("Import is designed for Beanstalk environment")
            logger.warning("Running locally may fail due to network restrictions")

        if not self.dump_s3_key:
            logger.error("Specify dump S3 key with --dump-key parameter")
            return False

        # Step 1: Download dump from S3
        local_dump = self.config["temp_path"] / "import_dump.sql"
        logger.info(f"Downloading: s3://{self.config['s3_bucket']}/{self.dump_s3_key}")

        try:
            self.s3_client.download_file(
                self.config["s3_bucket"], self.dump_s3_key, str(local_dump)
            )
            file_size_mb = local_dump.stat().st_size / 1024 / 1024
            logger.info(f"✓ Downloaded dump: {file_size_mb:.2f} MB")
        except Exception as e:
            logger.error(f"Failed to download dump: {e}")
            return False

        # Step 2: Import to Aurora
        logger.info("Importing to Aurora database...")
        password = self.get_aurora_password()

        try:
            conn = psycopg2.connect(
                host=self.config["aurora_endpoint"],
                port=5432,
                database=self.config["aurora_database"],
                user=self.config["aurora_username"],
                password=password,
                sslmode="require",
                connect_timeout=60,
            )

            with open(local_dump) as f:
                sql_content = f.read()

            cursor = conn.cursor()

            # Try single transaction first (fastest)
            try:
                logger.info("Attempting single-transaction import...")
                cursor.execute(sql_content)
                conn.commit()
                logger.info("✓ Database imported successfully")

            except psycopg2.Error as e:
                logger.warning(f"Single transaction failed: {str(e)[:100]}")
                logger.info("Retrying with statement-by-statement execution...")
                conn.rollback()

                # Split and execute statements
                statements = sqlparse.split(sql_content)
                statements = [s for s in statements if s.strip()]

                success_count = 0
                error_count = 0

                with tqdm(total=len(statements), desc="Importing") as pbar:
                    for stmt in statements:
                        try:
                            cursor.execute(stmt)
                            conn.commit()
                            success_count += 1
                        except psycopg2.Error as stmt_error:
                            conn.rollback()
                            if "already exists" not in str(stmt_error).lower():
                                error_count += 1
                        pbar.update(1)

                logger.info(
                    f"✓ Import complete: {success_count} successful, {error_count} errors"
                )

            cursor.close()
            conn.close()

            # Step 3: Verify
            logger.info("\nVerifying migration...")
            self.verify_migration()

            logger.info(f"\n{'=' * 60}")
            logger.info("✓ MIGRATION COMPLETED SUCCESSFULLY!")
            logger.info(f"{'=' * 60}")

            return True

        except Exception as e:
            logger.error(f"Import failed: {e}")
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=5, max=30),
        retry=retry_if_exception_type(psycopg2.OperationalError),
    )
    def verify_migration(self):
        """Quick verification of migrated data"""
        password = self.get_aurora_password()

        conn = psycopg2.connect(
            host=self.config["aurora_endpoint"],
            port=5432,
            database=self.config["aurora_database"],
            user=self.config["aurora_username"],
            password=password,
            sslmode="require",
        )

        cursor = conn.cursor()

        # Check key tables
        for table in ["companies", "filings", "analyses"]:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logger.info(f"  {table}: {count} records")
            except Exception as exc:
                logger.warning(
                    f"  {table}: not found or empty ({exc.__class__.__name__}: {exc})"
                )

        cursor.close()
        conn.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Simplified AWS Migration (2-step process)"
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--export",
        action="store_true",
        help="Export local database and upload to S3 (run locally)",
    )
    group.add_argument(
        "--import",
        action="store_true",
        dest="import_",
        help="Import database from S3 to Aurora (run on Beanstalk)",
    )

    parser.add_argument(
        "--dump-key", help="S3 key for database dump (required for --import)"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.import_ and not args.dump_key:
        logger.error("--import requires --dump-key")
        sys.exit(1)

    # Initialize migration handler
    migration = SimplifiedAWSMigration(dump_s3_key=args.dump_key)
    migration.setup_aws_clients()

    if not migration.find_s3_bucket():
        sys.exit(1)

    # Execute appropriate operation
    try:
        if args.export:
            success = migration.export_and_upload()
        else:  # args.import_
            success = migration.download_and_import()

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
