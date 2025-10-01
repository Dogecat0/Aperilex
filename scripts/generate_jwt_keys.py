"""Utility for generating JWT signing keys into the mounted secrets directory."""

from __future__ import annotations

import argparse
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

DEFAULT_PRIVATE_NAME = "JWT_PRIVATE_KEY"
DEFAULT_PUBLIC_NAME = "JWT_PUBLIC_KEY"
LOG_FILE_NAME = "JWT_KEY_ROTATION.log"


def _prepare_target(path: Path, *, force: bool) -> None:
    """Ensure target path is ready for writing a secret file."""

    if path.exists():
        if path.is_dir():
            if not force:
                raise SystemExit(
                    f"Cannot write key: '{path}' is a directory. Remove it or rerun with --force."
                )
            shutil.rmtree(path)
        elif not force:
            raise SystemExit(
                f"Refusing to overwrite existing file '{path}'. Pass --force to rotate keys."
            )
        else:
            path.unlink()


def _write_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    os.chmod(path, 0o600)


def _record_rotation(log_file: Path, private_path: Path) -> None:
    timestamp = datetime.now(UTC).isoformat()
    entry = f"[{timestamp}] rotated keys -> {private_path.name}\n"
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(entry)


def generate_keys(key_size: int, public_exponent: int) -> tuple[bytes, bytes]:
    """Generate a new RSA key pair for JWT signing."""

    private_key = rsa.generate_private_key(
        public_exponent=public_exponent,
        key_size=key_size,
    )
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_bytes, public_bytes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate JWT signing keys in the mounted secrets directory.",
    )
    parser.add_argument(
        "--secrets-dir",
        default=os.environ.get("DOCKER_SECRETS_DIR", ".secrets"),
        help="Directory where docker secrets are stored (default: %(default)s)",
    )
    parser.add_argument(
        "--private-name",
        default=DEFAULT_PRIVATE_NAME,
        help="Filename to use for the private key (default: %(default)s)",
    )
    parser.add_argument(
        "--public-name",
        default=DEFAULT_PUBLIC_NAME,
        help="Filename to use for the public key (default: %(default)s)",
    )
    parser.add_argument(
        "--key-size",
        type=int,
        default=4096,
        help="RSA key size in bits (default: %(default)s)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing key files instead of aborting",
    )
    args = parser.parse_args()

    secrets_path = Path(args.secrets_dir).expanduser().resolve()
    secrets_path.mkdir(parents=True, exist_ok=True)

    private_path = secrets_path / args.private_name
    public_path = secrets_path / args.public_name

    for target in (private_path, public_path):
        _prepare_target(target, force=args.force)

    private_bytes, public_bytes = generate_keys(args.key_size, public_exponent=65537)

    _write_file(private_path, private_bytes)
    _write_file(public_path, public_bytes)

    rotation_log = secrets_path / LOG_FILE_NAME
    _record_rotation(rotation_log, private_path)

    print(f"✅ Generated new JWT key pair in {secrets_path}")
    print(f"   Private key: {private_path.name}")
    print(f"   Public key:  {public_path.name}")
    print(f"   Rotation log: {rotation_log}")


if __name__ == "__main__":
    main()
