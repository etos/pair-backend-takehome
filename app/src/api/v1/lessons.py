import logging
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, ConfigDict, Field
from src import services as svc

logging.captureWarnings(True)
router = APIRouter()


class Lesson(BaseModel):
    id: int = Field(...)
    slug: str | None = None
    title: str | None = None

class Variant(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(...)
    tenant_id: int | None = None
    data: dict | None = None
    progress: str | None = None

class Block(BaseModel):
    id: int = Field(...)
    type: str | None = None
    position: int | None = None
    variant: Variant | None = None

class Progress(BaseModel):
    total_blocks: int | None = None
    seen_blocks: int | None = None
    completed_blocks: int | None = None
    last_seen_block_id: int | None = None
    completed: str | None = "false"

class Data(BaseModel):
    lesson: Lesson
    blocks: list[Block]
    progress_summary: Progress

class Root(BaseModel):
    data: Data


@router.get(
    "/tenants/{tenant_id}/users/{user_id}/lessons/{lesson_id}",
    response_model=Root,
    response_model_by_alias=False,
)
async def get_lesson(
    tenant_id: str = Path(..., min_length=1),
    user_id: str = Path(..., min_length=1),
    lesson_id: str = Path(..., min_length=1),
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

    return {"data": data}
