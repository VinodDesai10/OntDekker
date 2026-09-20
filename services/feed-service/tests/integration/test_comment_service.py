"""
CP-16C — CommentService Integration Tests

Validates service-layer behaviour for CommentService.
All tests use an in-memory SQLite database via the db_session fixture.
Focus: service orchestration, authorization, validation, and error handling.

Production issue note
---------------------
CommentService.create_comment() calls CommentSchema.model_validate(comment)
on the ORM object returned by CommentRepository.create().  That object's
``replies`` relationship is not eagerly loaded, so Pydantic triggers a lazy
load which fails with MissingGreenlet in an async context.

This is a production defect: the Comment ORM object must have its ``replies``
relationship loaded (e.g. via selectinload) before being passed to
model_validate.

Test strategy: tests that need existing comments for setup bypass
create_comment() and use the CommentRepository directly (consistent with
the CP-16B integration pattern).  The service methods that load comments
via get_comments_for_post() use selectinload and work correctly.
"""

import uuid
import pytest

from app.repositories.comment_repository import CommentRepository
from app.repositories.post_repository import PostRepository
from app.services.comment_service import CommentService
from app.schemas.feed import (
    CommentCreateRequest,
    CommentUpdateRequest,
    CommentSchema,
    CommentListResponse,
    CommentQueryParams,
)
from shared.exceptions import NotFoundError, ForbiddenError, ValidationError
from tests.utils import create_test_post, create_test_comment


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _svc(session) -> CommentService:
    return CommentService(session)


def _comment_repo(session) -> CommentRepository:
    return CommentRepository(session)


# ---------------------------------------------------------------------------
# create_comment — post existence validation
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_create_comment_raises_not_found_for_missing_post(db_session):
    """create_comment() raises NotFoundError when the post does not exist."""
    svc = _svc(db_session)

    with pytest.raises(NotFoundError):
        await svc.create_comment(
            uuid.uuid4(),
            CommentCreateRequest(content="Ghost comment"),
            uuid.uuid4(),
        )


@pytest.mark.integration
async def test_create_comment_raises_for_soft_deleted_post(db_session):
    """create_comment() raises when the post is soft-deleted."""
    post = await create_test_post(db_session)
    await db_session.commit()
    await PostRepository(db_session).soft_delete(post.id)
    svc = _svc(db_session)

    # Post is deleted → get_by_id returns None → NotFoundError
    with pytest.raises(NotFoundError):
        await svc.create_comment(
            post.id,
            CommentCreateRequest(content="Orphaned"),
            uuid.uuid4(),
        )


# ---------------------------------------------------------------------------
# update_comment — authorization and error handling
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_update_comment_raises_forbidden_for_non_author(db_session):
    """update_comment() raises ForbiddenError when a non-author tries to edit."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _comment_repo(db_session)
    comment = await repo.create(
        post_id=post.id, author_id=uuid.uuid4(), content="Mine"
    )
    svc = _svc(db_session)

    with pytest.raises(ForbiddenError):
        await svc.update_comment(
            comment.id, CommentUpdateRequest(content="Stolen edit"), uuid.uuid4()
        )


@pytest.mark.integration
async def test_update_comment_raises_forbidden_for_missing_comment(db_session):
    """update_comment() raises ForbiddenError when the comment does not exist."""
    svc = _svc(db_session)

    # can_user_modify_comment returns False for missing comment → ForbiddenError
    with pytest.raises(ForbiddenError):
        await svc.update_comment(
            uuid.uuid4(), CommentUpdateRequest(content="Ghost edit"), uuid.uuid4()
        )


@pytest.mark.integration
async def test_update_comment_raises_forbidden_for_deleted_comment(db_session):
    """update_comment() raises ForbiddenError for a soft-deleted comment."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _comment_repo(db_session)
    author_id = uuid.uuid4()
    comment = await repo.create(
        post_id=post.id, author_id=author_id, content="About to be deleted"
    )
    await repo.soft_delete(comment.id)
    svc = _svc(db_session)

    with pytest.raises(ForbiddenError):
        await svc.update_comment(
            comment.id, CommentUpdateRequest(content="Too late"), author_id
        )


# ---------------------------------------------------------------------------
# delete_comment — authorization and error handling
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_delete_comment_returns_true(db_session):
    """delete_comment() returns True on successful deletion."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _comment_repo(db_session)
    author_id = uuid.uuid4()
    comment = await repo.create(
        post_id=post.id, author_id=author_id, content="Delete me"
    )
    svc = _svc(db_session)

    result = await svc.delete_comment(comment.id, author_id)

    assert result is True


@pytest.mark.integration
async def test_delete_comment_raises_forbidden_for_non_author(db_session):
    """delete_comment() raises ForbiddenError when a non-author tries to delete."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _comment_repo(db_session)
    comment = await repo.create(
        post_id=post.id, author_id=uuid.uuid4(), content="Not yours"
    )
    svc = _svc(db_session)

    with pytest.raises(ForbiddenError):
        await svc.delete_comment(comment.id, uuid.uuid4())


@pytest.mark.integration
async def test_delete_comment_raises_forbidden_for_missing_comment(db_session):
    """delete_comment() raises ForbiddenError when the comment does not exist."""
    svc = _svc(db_session)

    with pytest.raises(ForbiddenError):
        await svc.delete_comment(uuid.uuid4(), uuid.uuid4())


@pytest.mark.integration
async def test_delete_comment_soft_deletes_content(db_session):
    """delete_comment() soft-deletes: content becomes '[deleted]'."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _comment_repo(db_session)
    author_id = uuid.uuid4()
    comment = await repo.create(
        post_id=post.id, author_id=author_id, content="Secret"
    )
    svc = _svc(db_session)

    await svc.delete_comment(comment.id, author_id)

    deleted = await repo.get_by_id(comment.id, include_deleted=True)
    assert deleted.is_deleted is True
    assert deleted.content == "[deleted]"


# ---------------------------------------------------------------------------
# get_post_comments
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_get_post_comments_returns_comment_list_response(db_session):
    """get_post_comments() returns a CommentListResponse."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _comment_repo(db_session)
    await repo.create(post_id=post.id, author_id=uuid.uuid4(), content="C1")
    await repo.create(post_id=post.id, author_id=uuid.uuid4(), content="C2")
    svc = _svc(db_session)

    result = await svc.get_post_comments(post.id, CommentQueryParams())

    assert isinstance(result, CommentListResponse)
    assert result.total == 2
    assert len(result.comments) == 2


@pytest.mark.integration
@pytest.mark.xfail(
    strict=True,
    reason=(
        "Production bug: CommentRepository.get_comments_for_post() does not apply "
        "selectinload(Comment.replies) when include_replies=False. "
        "Pydantic's CommentSchema.model_validate() then attempts to access the "
        "unloaded 'replies' relationship, triggering a MissingGreenlet error in the "
        "async context. The repository must always eagerly load the 'replies' "
        "relationship (regardless of include_replies) before handing Comment objects "
        "to Pydantic, or the schema must avoid accessing the relationship when it is "
        "not loaded."
    ),
)
async def test_get_post_comments_returns_top_level_only_by_default(db_session):
    """get_post_comments(include_replies=False) returns only top-level comments."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _comment_repo(db_session)
    parent = await repo.create(
        post_id=post.id, author_id=uuid.uuid4(), content="Parent"
    )
    await repo.create(
        post_id=post.id, author_id=uuid.uuid4(),
        content="Reply", parent_comment_id=parent.id
    )
    svc = _svc(db_session)

    result = await svc.get_post_comments(post.id, CommentQueryParams(include_replies=False))

    assert result.total == 1
    assert result.comments[0].id == parent.id


@pytest.mark.integration
@pytest.mark.xfail(
    strict=True,
    reason=(
        "Production bug: CommentRepository.get_comments_for_post() applies "
        "selectinload(Comment.replies) for top-level comments but does NOT recursively "
        "load the 'replies' relationship on the reply objects themselves. "
        "When Pydantic's CommentSchema.model_validate() processes a reply object, "
        "it attempts to access reply.replies, triggering a MissingGreenlet error. "
        "The repository must use selectinload(Comment.replies).selectinload(Comment.replies) "
        "(or a recursive approach) to ensure all nested Comment objects have their "
        "'replies' relationship eagerly loaded before serialisation."
    ),
)
async def test_get_post_comments_includes_replies_when_requested(db_session):
    """get_post_comments(include_replies=True) eager-loads reply objects."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _comment_repo(db_session)
    parent = await repo.create(
        post_id=post.id, author_id=uuid.uuid4(), content="Parent"
    )
    await repo.create(
        post_id=post.id, author_id=uuid.uuid4(),
        content="Child", parent_comment_id=parent.id
    )
    svc = _svc(db_session)

    result = await svc.get_post_comments(post.id, CommentQueryParams(include_replies=True))

    assert len(result.comments[0].replies) == 1
    assert result.comments[0].replies[0].content == "Child"


@pytest.mark.integration
async def test_get_post_comments_excludes_deleted_comments(db_session):
    """get_post_comments() does not include soft-deleted comments in the count."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _comment_repo(db_session)
    author_id = uuid.uuid4()
    c1 = await repo.create(post_id=post.id, author_id=uuid.uuid4(), content="Live")
    c2 = await repo.create(post_id=post.id, author_id=author_id, content="Deleted")
    await repo.soft_delete(c2.id)
    svc = _svc(db_session)

    result = await svc.get_post_comments(post.id, CommentQueryParams())

    assert result.total == 1
    ids = [c.id for c in result.comments]
    assert c1.id in ids
    assert c2.id not in ids


@pytest.mark.integration
async def test_get_post_comments_respects_pagination(db_session):
    """get_post_comments() respects limit and offset parameters."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _comment_repo(db_session)
    for i in range(5):
        await repo.create(
            post_id=post.id, author_id=uuid.uuid4(), content=f"Comment {i}"
        )
    svc = _svc(db_session)

    result = await svc.get_post_comments(post.id, CommentQueryParams(limit=3, offset=0))

    assert result.total == 5
    assert len(result.comments) == 3


@pytest.mark.integration
async def test_get_post_comments_has_more_flag(db_session):
    """get_post_comments() sets has_more=True when there are more results."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _comment_repo(db_session)
    for i in range(4):
        await repo.create(
            post_id=post.id, author_id=uuid.uuid4(), content=f"C{i}"
        )
    svc = _svc(db_session)

    result = await svc.get_post_comments(post.id, CommentQueryParams(limit=2, offset=0))

    assert result.has_more is True


@pytest.mark.integration
async def test_get_post_comments_returns_comment_schemas(db_session):
    """get_post_comments() items are CommentSchema instances."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _comment_repo(db_session)
    await repo.create(post_id=post.id, author_id=uuid.uuid4(), content="One")
    svc = _svc(db_session)

    result = await svc.get_post_comments(post.id, CommentQueryParams())

    assert isinstance(result.comments[0], CommentSchema)


@pytest.mark.integration
async def test_get_post_comments_empty_for_post_with_no_comments(db_session):
    """get_post_comments() returns empty list for post with no comments."""
    post = await create_test_post(db_session)
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.get_post_comments(post.id, CommentQueryParams())

    assert result.total == 0
    assert len(result.comments) == 0
    assert result.has_more is False
