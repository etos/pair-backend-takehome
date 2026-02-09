import logging
from typing import Literal
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, ConfigDict, Field
from src import services as svc

logging.captureWarnings(True)
router = APIRouter()


class ProgressUpsertRequest(BaseModel):
    block_id: int = Field(...)
    status: Literal["seen", "completed"] = Field(...)


class ProgressUpsertResponse(BaseModel):
    stored_status: Literal["seen", "completed"]
    progress_summary: "Progress"


class Lesson(BaseModel):
    id: int = Field(...)
    slug: str | None = None
    title: str | None = None

class Variant(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(...)
    tenant_id: int | None = None
    data: dict | None = None

class Block(BaseModel):
    id: int = Field(...)
    type: str | None = None
    position: int | None = None
    variant: Variant | None = None
    user_progress: str | None = None

class Progress(BaseModel):
    total_blocks: int | None = None
    seen_blocks: int | None = None
    completed_blocks: int | None = None
    last_seen_block_id: int | None = None
    completed: bool | None = False

class Root(BaseModel):
    lesson: Lesson
    blocks: list[Block]
    progress_summary: Progress


@router.get(
    "/tenants/{tenant_id}/users/{user_id}/lessons/{lesson_id}",
    response_model=Root,
    response_model_by_alias=False,
)
async def get_lesson(
    tenant_id: int = Path(..., gt=0),
    user_id: int = Path(..., gt=0),
    lesson_id: int = Path(..., gt=0),
):
    """
    Retrieve lesson for a tenant -> user.
    """
    data = await svc.lessons.get_lesson(
        tenant_id=tenant_id,
        user_id=user_id,
        lesson_id=lesson_id,
    )

    if not data:
        raise HTTPException(status_code=404, detail="lesson not found.")

    return data


@router.put(
    "/tenants/{tenant_id}/users/{user_id}/lessons/{lesson_id}/progress",
    response_model=ProgressUpsertResponse,
    response_model_by_alias=False,
)
async def upsert_progress(
    body: ProgressUpsertRequest,
    tenant_id: int = Path(..., gt=0),
    user_id: int = Path(..., gt=0),
    lesson_id: int = Path(..., gt=0),
):
    """
    Upsert progress for a single block (idempotent).
    Monotonic: completed cannot be downgraded to seen.
    """
    result = await svc.lessons.upsert_progress(
        tenant_id=tenant_id,
        user_id=user_id,
        lesson_id=lesson_id,
        block_id=body.block_id,
        status=body.status,
    )

    if result is None:
        raise HTTPException(status_code=404, detail="tenant, user, or lesson not found.")

    if result.get("error") == "block_not_in_lesson":
        raise HTTPException(status_code=400, detail="block_id not in lesson.")

    return result
