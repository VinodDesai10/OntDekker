"""
User Service — MinIO Storage Client

Wraps the minio Python SDK for async-safe use via asyncio.to_thread().
The MinIO SDK is synchronous; all calls are dispatched to a thread pool
to avoid blocking the event loop.

Responsibilities:
  - Ensure the profiles bucket exists on startup (idempotent).
  - Upload avatar and cover images.
  - Generate pre-signed GET URLs for private objects (time-limited).
  - Delete objects (used during replacement and cleanup).

Security rules enforced here:
  - Credentials are never logged.
  - The profiles bucket is PRIVATE (no public policy set).
  - Object names are server-generated; the original filename is never used as the key.
  - Content-type and size validation is done at the API layer before calling here.
"""

import asyncio
import logging
import uuid
from io import BytesIO
from datetime import timedelta

from minio import Minio
from minio.error import S3Error

from app.config.settings import settings

logger = logging.getLogger(__name__)


def _make_client() -> Minio:
    """Build a Minio client from current settings. Called once at startup."""
    return Minio(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_USE_SSL,
    )


# Module-level singleton — created in lifespan, used by dependency injection.
_minio_client: Minio | None = None


def get_raw_client() -> Minio:
    """Return the module-level Minio client (raises if not initialised)."""
    if _minio_client is None:
        raise RuntimeError("MinIO client has not been initialised. Check lifespan setup.")
    return _minio_client


async def init_minio() -> None:
    """
    Initialise the MinIO client and ensure the profiles bucket exists.
    Called once during FastAPI lifespan startup.
    No error is raised if the bucket already exists (idempotent).
    """
    global _minio_client
    _minio_client = _make_client()
    bucket = settings.MINIO_BUCKET_PROFILES

    def _ensure_bucket():
        try:
            if not _minio_client.bucket_exists(bucket):
                _minio_client.make_bucket(bucket)
                logger.info("MinIO bucket created", extra={"extra_data": {"bucket": bucket}})
            else:
                logger.info("MinIO bucket ready", extra={"extra_data": {"bucket": bucket}})
        except S3Error as exc:
            # Log without exposing credentials
            logger.error("MinIO bucket init failed: %s", exc.code)
            raise

    await asyncio.to_thread(_ensure_bucket)


async def upload_object(
    object_name: str,
    data: bytes,
    content_type: str,
) -> str:
    """
    Upload bytes to the profiles bucket under the given object_name.

    Returns the object_name (the caller stores this reference in the DB).
    Raises S3Error on upload failure — the caller must not update the DB
    if this raises.

    The bucket is PRIVATE; callers use presigned_url() to generate
    time-limited access URLs for the frontend.
    """
    client = get_raw_client()
    bucket = settings.MINIO_BUCKET_PROFILES
    length = len(data)

    def _upload():
        client.put_object(
            bucket_name=bucket,
            object_name=object_name,
            data=BytesIO(data),
            length=length,
            content_type=content_type,
        )

    await asyncio.to_thread(_upload)
    logger.info(
        "Object uploaded to MinIO",
        extra={"extra_data": {"bucket": bucket, "object": object_name, "bytes": length}},
    )
    return object_name


async def presigned_url(object_name: str, expires_hours: int = 1) -> str:
    """
    Generate a pre-signed GET URL for a private object.

    The URL is valid for `expires_hours` hours.

    If MINIO_PUBLIC_URL is set, the internal Docker hostname in the presigned
    URL is replaced with the browser-accessible host so that the browser can
    actually load the image.  Without this, the URL contains "minio:9000"
    which resolves only inside the Docker network, not in the user's browser.

    The URL is not logged (it grants temporary access to private content).
    """
    client = get_raw_client()
    bucket = settings.MINIO_BUCKET_PROFILES
    expiry = timedelta(hours=expires_hours)

    def _presign():
        return client.presigned_get_object(
            bucket_name=bucket,
            object_name=object_name,
            expires=expiry,
        )

    url = await asyncio.to_thread(_presign)

    # Rewrite the internal Docker hostname to the browser-accessible public URL
    # so that the frontend can actually load the image.
    if settings.MINIO_PUBLIC_URL:
        # Replace the scheme+host portion that the Minio SDK used (MINIO_ENDPOINT)
        # with the public URL. We handle both http and https.
        internal_endpoint = settings.MINIO_ENDPOINT
        public_endpoint = settings.MINIO_PUBLIC_URL
        # Build the full scheme://host for both sides
        scheme = "https" if settings.MINIO_USE_SSL else "http"
        internal_prefix = f"{scheme}://{internal_endpoint}"
        public_prefix = f"{scheme}://{public_endpoint}"
        if url.startswith(internal_prefix):
            url = public_prefix + url[len(internal_prefix):]

    return url


async def delete_object(object_name: str) -> None:
    """Delete an object from the profiles bucket. Silent if it does not exist."""
    client = get_raw_client()
    bucket = settings.MINIO_BUCKET_PROFILES

    def _delete():
        try:
            client.remove_object(bucket_name=bucket, object_name=object_name)
        except S3Error as exc:
            if exc.code == "NoSuchKey":
                pass  # Already gone — treat as success
            else:
                raise

    await asyncio.to_thread(_delete)


def make_avatar_object_name(user_id: uuid.UUID, extension: str) -> str:
    """
    Generate a deterministic avatar object name for a user.
    Using the user_id means uploading a new avatar silently replaces the old one
    (same key) — no orphaned objects, no cleanup needed.
    """
    ext = extension.lstrip(".").lower()
    return f"avatars/{user_id}.{ext}"


def make_cover_object_name(user_id: uuid.UUID, extension: str) -> str:
    """Generate a deterministic cover object name."""
    ext = extension.lstrip(".").lower()
    return f"covers/{user_id}.{ext}"
