"""
Feed Service — Media Business Logic

Service class for media upload URL generation and post media metadata persistence.
Uses the official MinIO Python SDK (minio>=7.2.0) for presigned URL generation
and bucket management.
"""

import asyncio
import json
import uuid
from datetime import timedelta
from typing import Optional

from minio import Minio
from minio.error import S3Error
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.repositories import PostRepository
from app.schemas.feed import MediaUploadRequest, MediaUploadResponse, PostMediaCreateRequest
from shared.exceptions import NotFoundError, ForbiddenError

# MinIO bucket for post media
POST_BUCKET = "posts"

# MinIO / S3 region.  MinIO uses us-east-1 by default and this value is present
# in every presigned URL credential string.  Pre-setting the region on SDK
# clients that cannot reach MinIO over the network (e.g. the public client that
# uses localhost:9000 inside the container) allows those clients to skip the
# GetBucketLocation HTTP call that _get_region() would otherwise make.
_MINIO_REGION = "us-east-1"


def _build_minio_client() -> Minio:
    """Construct a MinIO client using the internal Docker endpoint (minio:9000).

    Used for operations that require a live connection to MinIO: bucket existence
    checks and bucket creation.
    """
    return Minio(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


def _build_minio_public_client() -> Minio:
    """Construct a MinIO client using the browser-accessible endpoint (localhost:9000).

    Used exclusively for presigned URL generation.  Presigned URLs produced by
    this client embed localhost:9000 as the host, making them directly usable by
    browsers outside the Docker network.

    WHY THIS WORKS WITHOUT A LIVE CONNECTION TO localhost:9000:
    The MinIO SDK's _get_region() makes an HTTP GET /<bucket>?location= request
    to resolve the bucket region, but ONLY when the region is not already known.
    By passing region=_MINIO_REGION we bypass that HTTP call entirely — the SDK
    uses the pre-set value and proceeds directly to signing the URL.  No real
    network connection to localhost:9000 is ever opened during URL generation.

    The resulting URL is signed with host=localhost:9000, so when a browser sends
    the PUT request to localhost:9000 the HMAC-SHA256 signature is valid.
    """
    return Minio(
        endpoint=settings.MINIO_PUBLIC_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
        region=_MINIO_REGION,  # pre-set → skips GetBucketLocation HTTP call
    )


def _ensure_bucket(client: Minio, bucket: str) -> None:
    """Create the bucket if it does not already exist, then ensure it has a
    public-read policy so browsers can fetch uploaded objects directly via
    their stored media_url (http://localhost:9000/{bucket}/...).

    MinIO buckets are private by default.  Without a public-read policy every
    unauthenticated GET request to the stored media_url returns 403
    AccessDenied, causing broken images in the feed even when the upload
    succeeded.  Setting the policy here is idempotent — it is re-applied on
    every presigned URL generation call, which is fine for local development.
    """
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)

    # S3-compatible public-read bucket policy
    public_read_policy = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{bucket}/*"],
                }
            ],
        }
    )
    client.set_bucket_policy(bucket, public_read_policy)


class MediaService:
    """Business logic for post media upload management."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.post_repo = PostRepository(session)

    # -------------------------------------------------------------------------
    # Presigned URL generation
    # -------------------------------------------------------------------------

    async def generate_upload_url(
        self,
        post_id: uuid.UUID,
        request: MediaUploadRequest,
        user_id: uuid.UUID,
    ) -> MediaUploadResponse:
        """Generate a presigned PUT URL for uploading media to a post.

        Post author only.
        """
        post = await self.post_repo.get_by_id(post_id)
        if not post:
            raise NotFoundError(f"Post {post_id} not found")

        if post.author_id != user_id:
            raise ForbiddenError("You can only upload media to your own posts")

        ext = self._get_extension(request.filename)
        object_key = f"{POST_BUCKET}/{post_id}/{uuid.uuid4()}{ext}"

        # MinIO SDK calls are synchronous — run in the default thread pool executor
        # so we do not block the async event loop.
        loop = asyncio.get_event_loop()
        upload_url = await loop.run_in_executor(
            None,
            self._generate_presigned_put_url,
            object_key,
        )

        return MediaUploadResponse(
            upload_url=upload_url,
            object_key=object_key,
            expires_in=3600,
        )

    # -------------------------------------------------------------------------
    # Media metadata persistence (called after client uploads to MinIO)
    # -------------------------------------------------------------------------

    async def associate_media_with_post(
        self,
        post_id: uuid.UUID,
        request: PostMediaCreateRequest,
        user_id: uuid.UUID,
    ):
        """Associate uploaded media metadata with a post.

        The client has already uploaded the binary to MinIO before calling this.
        Derives the permanent public media_url from the object_key using the
        configured public MinIO endpoint so the URL is browser-accessible.

        Post author only.
        """
        post = await self.post_repo.get_by_id(post_id)
        if not post:
            raise NotFoundError(f"Post {post_id} not found")

        if post.author_id != user_id:
            raise ForbiddenError("You can only add media to your own posts")

        # Build a permanent public URL using the browser-accessible endpoint.
        # object_key already includes the bucket prefix (posts/<post_id>/<uuid>.ext).
        # This is pure string construction — no SDK call, no signature involved.
        scheme = "https" if settings.MINIO_SECURE else "http"
        media_url = f"{scheme}://{settings.MINIO_PUBLIC_ENDPOINT}/{request.object_key}"

        media = await self.post_repo.add_media(
            post_id=post_id,
            media_url=media_url,
            object_key=request.object_key,
            display_order=request.display_order,
            alt_text=request.alt_text,
            created_by=user_id,
        )

        return media

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _generate_presigned_put_url(self, object_key: str) -> str:
        """Synchronous helper: ensure bucket exists, then return a presigned PUT URL.

        Runs inside a thread pool executor (called via run_in_executor).

        Two clients are used for different reasons:
        - Internal client (_build_minio_client): connects to minio:9000 to check
          / create the bucket.  This requires a real network call inside Docker.
        - Public client (_build_minio_public_client): generates the presigned URL
          with localhost:9000 as the host.  Region is pre-set so no network call
          is made.  The resulting URL is valid for browser PUT requests.

        Object-key normalisation:
        The stored object_key has the form  posts/{post_id}/{uuid}.ext.  When
        calling the SDK we strip the leading "posts/" prefix because the SDK
        inserts the bucket name in the URL path itself:
          presigned_put_object("posts", "{post_id}/{uuid}.ext")
          → http://localhost:9000/posts/{post_id}/{uuid}.ext?…   (correct)
        Passing the full key would produce the doubled path /posts/posts/…
        """
        # Bucket ops require a live connection — use internal client
        internal_client = _build_minio_client()
        _ensure_bucket(internal_client, POST_BUCKET)

        # URL generation uses public client — region pre-set, no network call
        public_client = _build_minio_public_client()
        bucket_prefix = POST_BUCKET + "/"
        sdk_object_name = (
            object_key[len(bucket_prefix):]
            if object_key.startswith(bucket_prefix)
            else object_key
        )

        return public_client.presigned_put_object(
            POST_BUCKET,
            sdk_object_name,
            expires=timedelta(hours=1),
        )

    @staticmethod
    def _get_extension(filename: str) -> str:
        """Extract the file extension, defaulting to .jpg."""
        if "." in filename:
            return "." + filename.rsplit(".", 1)[-1].lower()
        return ".jpg"
