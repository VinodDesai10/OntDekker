"""
Community Service — Media Business Logic

Service class that handles presigned URL generation for community logos
and banners, and persists the resulting object keys after upload.
Uses the official MinIO Python SDK (minio>=7.2.0) for presigned URL generation
and bucket management.
"""

import asyncio
import json
import uuid
from datetime import timedelta

from minio import Minio
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.repositories import CommunityRepository, MembershipRepository
from app.schemas.community import (
    MediaUploadRequest,
    MediaUploadResponse,
    CommunityMediaSetRequest,
    CommunitySchema,
)
from shared.constants.status import MemberRole
from shared.exceptions import NotFoundError, ForbiddenError

# MinIO bucket for community media
COMMUNITY_BUCKET = "communities"

# S3 bucket policy that allows anonymous (public) GET on every object in the
# bucket.  This is required so the browser can load logo/banner images via
# their permanent http://localhost:9000/communities/… URLs without needing
# signed query-string credentials.
_PUBLIC_READ_POLICY = json.dumps({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"AWS": ["*"]},
            "Action": ["s3:GetObject"],
            "Resource": [f"arn:aws:s3:::{COMMUNITY_BUCKET}/*"],
        }
    ],
})


def _build_minio_client() -> Minio:
    """Construct a MinIO client for bucket management operations.

    Uses MINIO_ENDPOINT (internal Docker hostname, e.g. minio:9000) so the
    SDK can reach MinIO over the Docker network.
    """
    return Minio(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


def _build_presign_client() -> Minio:
    """Construct a MinIO client whose presigned URLs are signed with the
    public endpoint (MINIO_PUBLIC_ENDPOINT, e.g. localhost:9000).

    Problem: the SDK computes HMAC-SHA256 signatures using the hostname it
    was initialised with.  If we initialise with the internal hostname
    (minio:9000) the signature is computed over host=minio:9000.  After we
    rewrite the URL host to localhost:9000, MinIO re-derives the canonical
    request using host=localhost:9000 — the signatures don't match → 403.

    Solution: build a second client initialised with minio:9000 for TCP
    connectivity (so _get_region() can reach MinIO) then swap the internal
    _base_url._url netloc to localhost:9000 before generating presigned URLs.
    All subsequent URL construction and HMAC computation use localhost:9000,
    so the signature MinIO verifies against matches the Host header the
    browser sends.

    MINIO_SERVER_URL=http://localhost:9000 on the MinIO container instructs
    MinIO to treat localhost:9000 as its canonical host identity when
    verifying presigned-URL signatures — this is what makes the approach work.
    """
    import urllib.parse as _up

    client = Minio(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )

    # Pre-seed the region cache so presigned_put_object does not make a live
    # HTTP call to resolve the bucket region (which would fail if the bucket
    # doesn't exist yet, and is unnecessary overhead either way).
    client._region_map = {"communities": "us-east-1"}

    # Swap the netloc in _base_url._url from minio:9000 → localhost:9000 so
    # the URL path and HMAC signature are constructed with the public host.
    orig = client._base_url._url
    client._base_url._url = _up.SplitResult(
        scheme=orig.scheme,
        netloc=settings.MINIO_PUBLIC_ENDPOINT,   # e.g. "localhost:9000"
        path=orig.path,
        query=orig.query,
        fragment=orig.fragment,
    )

    return client


def _ensure_bucket(client: Minio, bucket: str) -> None:
    """Create the bucket if it does not already exist and apply a public-read
    policy so browsers can load logo/banner images without signed credentials.

    MinIO buckets are private by default — without this policy every GET
    request to http://localhost:9000/communities/… returns 403 even when the
    URL is structurally correct.
    """
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    # Always (re-)apply the policy so it is set even on buckets that were
    # created before this fix was deployed.
    client.set_bucket_policy(bucket, _PUBLIC_READ_POLICY)


class MediaService:
    """Business logic for community logo and banner management."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.community_repo = CommunityRepository(session)
        self.membership_repo = MembershipRepository(session)

    # -------------------------------------------------------------------------
    # Presigned URL generation
    # -------------------------------------------------------------------------

    async def generate_logo_upload_url(
        self,
        community_id: uuid.UUID,
        request: MediaUploadRequest,
        current_user_id: uuid.UUID,
    ) -> MediaUploadResponse:
        """Generate a presigned PUT URL for uploading a community logo.

        OWNER only.
        """
        await self._require_owner(community_id, current_user_id)

        ext = self._get_extension(request.filename)
        object_key = f"{COMMUNITY_BUCKET}/{community_id}/logo/{uuid.uuid4()}{ext}"

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

    async def generate_banner_upload_url(
        self,
        community_id: uuid.UUID,
        request: MediaUploadRequest,
        current_user_id: uuid.UUID,
    ) -> MediaUploadResponse:
        """Generate a presigned PUT URL for uploading a community banner.

        OWNER only.
        """
        await self._require_owner(community_id, current_user_id)

        ext = self._get_extension(request.filename)
        object_key = f"{COMMUNITY_BUCKET}/{community_id}/banner/{uuid.uuid4()}{ext}"

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
    # Media persistence (called after client uploads to MinIO)
    # -------------------------------------------------------------------------

    async def set_community_logo(
        self,
        community_id: uuid.UUID,
        request: CommunityMediaSetRequest,
        current_user_id: uuid.UUID,
    ) -> CommunitySchema:
        """Persist a logo object key after a successful client upload.

        Derives the permanent public URL from the object key using the
        MINIO_PUBLIC_ENDPOINT so the URL is reachable from the browser.
        OWNER only.
        """
        await self._require_owner(community_id, current_user_id)

        # Build a permanent public URL using the public-facing endpoint.
        # MINIO_PUBLIC_ENDPOINT is set to localhost:9000 so browsers can reach it.
        scheme = "https" if settings.MINIO_SECURE else "http"
        logo_url = f"{scheme}://{settings.MINIO_PUBLIC_ENDPOINT}/{request.object_key}"

        updated = await self.community_repo.update_logo(
            community_id=community_id,
            logo_url=logo_url,
            logo_object_key=request.object_key,
            updated_by=current_user_id,
        )
        # NOTE: community_repo.update_logo() delegates to community_repo.update()
        # which already calls session.commit() internally.  Do NOT call
        # session.commit() here — a second commit on the same (already-closed)
        # transaction raises sqlalchemy.exc.InvalidRequestError → HTTP 500.
        if not updated:
            raise NotFoundError(f"Community {community_id} not found")

        # Return the full community schema
        from app.services.community_service import CommunityService
        community_service = CommunityService(self.session)
        return await community_service._to_schema(updated, current_user_id)

    async def set_community_banner(
        self,
        community_id: uuid.UUID,
        request: CommunityMediaSetRequest,
        current_user_id: uuid.UUID,
    ) -> CommunitySchema:
        """Persist a banner object key after a successful client upload.

        OWNER only.
        """
        await self._require_owner(community_id, current_user_id)

        scheme = "https" if settings.MINIO_SECURE else "http"
        banner_url = f"{scheme}://{settings.MINIO_PUBLIC_ENDPOINT}/{request.object_key}"

        updated = await self.community_repo.update_banner(
            community_id=community_id,
            banner_url=banner_url,
            banner_object_key=request.object_key,
            updated_by=current_user_id,
        )
        # NOTE: community_repo.update_banner() delegates to community_repo.update()
        # which already calls session.commit() internally.  Do NOT call
        # session.commit() here — a second commit on the same (already-closed)
        # transaction raises sqlalchemy.exc.InvalidRequestError → HTTP 500.
        if not updated:
            raise NotFoundError(f"Community {community_id} not found")

        from app.services.community_service import CommunityService
        community_service = CommunityService(self.session)
        return await community_service._to_schema(updated, current_user_id)

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _generate_presigned_put_url(self, object_key: str) -> str:
        """Synchronous helper: ensure bucket exists, then return a presigned PUT URL.

        Runs inside a thread pool executor (called via run_in_executor).

        Two MinIO clients are used:
        - _build_minio_client()  → internal endpoint (minio:9000) for bucket
          management (bucket_exists, make_bucket, set_bucket_policy).
        - _build_presign_client() → internal TCP but public netloc in
          _base_url._url (localhost:9000) so the HMAC signature is computed
          over host=localhost:9000.

        MinIO is configured with MINIO_SERVER_URL=http://localhost:9000 so it
        treats localhost:9000 as its canonical host identity when verifying
        presigned-URL signatures.  The signature computed by _build_presign_client
        therefore matches what MinIO re-derives from the incoming request's
        Host: localhost:9000 header → 200 instead of 403 SignatureDoesNotMatch.
        """
        # Bucket management uses the internal client (can reach minio:9000)
        mgmt_client = _build_minio_client()
        _ensure_bucket(mgmt_client, COMMUNITY_BUCKET)

        # Presigned URL generation uses the public-netloc client so the
        # HMAC signature is tied to localhost:9000 (what the browser sends).
        presign_client = _build_presign_client()

        bucket_prefix = COMMUNITY_BUCKET + "/"
        sdk_object_name = (
            object_key[len(bucket_prefix):]
            if object_key.startswith(bucket_prefix)
            else object_key
        )

        return presign_client.presigned_put_object(
            COMMUNITY_BUCKET,
            sdk_object_name,
            expires=timedelta(hours=1),
        )

    async def _require_owner(self, community_id: uuid.UUID, user_id: uuid.UUID) -> None:
        community = await self.community_repo.get_by_id(community_id)
        if not community:
            raise NotFoundError(f"Community {community_id} not found")
        member = await self.membership_repo.get_active_member(community_id, user_id)
        if not member or member.role != MemberRole.OWNER:
            raise ForbiddenError("Only the community owner can manage media")

    @staticmethod
    def _get_extension(filename: str) -> str:
        """Extract the file extension, defaulting to .jpg."""
        if "." in filename:
            return "." + filename.rsplit(".", 1)[-1].lower()
        return ".jpg"
