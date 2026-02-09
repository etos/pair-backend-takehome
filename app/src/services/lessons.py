import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from src.conf import AppConfig

conf = AppConfig()
logging.basicConfig(level=conf.LOG_LEVEL)



async def get_lesson(tenant_id: int, user_id: int, lesson_id: int) -> dict | None:
    """
    Retrieve tenant > user > lesson.

    TODO: move db init to a central module
    TODO: remove wildcards in SQL
    """
    db = create_async_engine(conf.POSTGRES_URL)
    params = {"tenant_id": tenant_id, "user_id": user_id, "lesson_id": lesson_id}

    async with db.connect() as conn:
        rows = (await conn.execute(text("""
            SELECT
                l.id AS lesson_id,
                l.slug AS lesson_slug,
                l.title AS lesson_title,
                b.id AS block_id,
                b.block_type AS block_type,
                lb.position AS block_position,
                bv.id AS variant_id,
                bv.tenant_id AS variant_tenant_id,
                bv.data as variant_data,
                ubp.status AS progress_status,
                ubp.updated_at AS progress_updated_at
            FROM lessons l
            JOIN users u ON u.id = :user_id AND u.tenant_id = :tenant_id
            JOIN lesson_blocks lb ON lb.lesson_id = l.id
            JOIN blocks b ON b.id = lb.block_id
            LEFT JOIN LATERAL (
                SELECT *
                FROM block_variants v
                WHERE v.block_id = b.id
                  AND (v.tenant_id = :tenant_id OR v.tenant_id IS NULL)
                ORDER BY v.tenant_id NULLS LAST
                LIMIT 1
            ) bv ON TRUE
            LEFT JOIN user_block_progress ubp
                ON ubp.block_id  = lb.block_id
               AND ubp.lesson_id = l.id
               AND ubp.user_id = :user_id
            WHERE l.id = :lesson_id
              AND l.tenant_id = :tenant_id
            ORDER BY lb.position
            """
        ), params)).mappings().all()

    if not rows:
        return None

    statuses = [r["progress_status"] for r in rows]

    data = {
        "lesson": {
            "id": rows[0]["lesson_id"],
            "slug": rows[0]["lesson_slug"],
            "title": rows[0]["lesson_title"],
        },
        "blocks": [
            {
                "id": r["block_id"],
                "type": r["block_type"],
                "position": r["block_position"],
                "variant": {
                    "id": r["variant_id"],
                    "tenant_id": r["variant_tenant_id"],
                    "data": r["variant_data"],
                },
                "user_progress": r["progress_status"],
            }
            for r in rows
        ],
        "progress_summary": {
            "total_blocks": len(rows),
            "seen_blocks": sum(1 for s in statuses if s in ("seen", "completed")),
            "completed_blocks": sum(1 for s in statuses if s == "completed"),
            "last_seen_block_id": next(
                (r["block_id"] for r in reversed(rows) if r["progress_status"]),
                None,
            ),
            "completed": all(s == "completed" for s in statuses)
        }
    }

    return data


async def upsert_progress(
    tenant_id: int, user_id: int, lesson_id: int, block_id: int, status: str
) -> dict | None:
    """
    Upsert user progress for a block in a lesson.

    Returns None if tenant/user/lesson not found or user doesn't belong to tenant.
    Returns {"error": "block_not_in_lesson"} if block_id is not part of the lesson.
    Returns {"stored_status": ..., "progress_summary": ...} on success.
    """
    db = create_async_engine(conf.POSTGRES_URL)
    params = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "lesson_id": lesson_id,
        "block_id": block_id,
        "status": status,
    }

    async with db.connect() as conn:
        # Validate tenant, user, lesson relationships
        validation = (await conn.execute(text("""
            SELECT 1
            FROM lessons l
            JOIN users u ON u.id = :user_id AND u.tenant_id = :tenant_id
            WHERE l.id = :lesson_id AND l.tenant_id = :tenant_id
        """), params)).fetchone()

        if not validation:
            return None

        # Check if block_id is part of the lesson
        block_check = (await conn.execute(text("""
            SELECT 1 FROM lesson_blocks
            WHERE lesson_id = :lesson_id AND block_id = :block_id
        """), params)).fetchone()

        if not block_check:
            return {"error": "block_not_in_lesson"}

        # Upsert progress with monotonic constraint (don't downgrade completed -> seen)
        await conn.execute(text("""
            INSERT INTO user_block_progress (user_id, lesson_id, block_id, status, updated_at)
            VALUES (:user_id, :lesson_id, :block_id, :status, now())
            ON CONFLICT (user_id, lesson_id, block_id)
            DO UPDATE SET
                status = CASE
                    WHEN user_block_progress.status = 'completed' THEN 'completed'
                    ELSE EXCLUDED.status
                END,
                updated_at = now()
        """), params)
        await conn.commit()

        # Get the stored status
        stored_row = (await conn.execute(text("""
            SELECT status FROM user_block_progress
            WHERE user_id = :user_id AND lesson_id = :lesson_id AND block_id = :block_id
        """), params)).fetchone()
        stored_status = stored_row[0]

        # Calculate progress summary
        summary_rows = (await conn.execute(text("""
            SELECT lb.block_id, ubp.status
            FROM lesson_blocks lb
            LEFT JOIN user_block_progress ubp
                ON ubp.block_id = lb.block_id
               AND ubp.lesson_id = lb.lesson_id
               AND ubp.user_id = :user_id
            WHERE lb.lesson_id = :lesson_id
            ORDER BY lb.position
        """), params)).fetchall()

        statuses = [r[1] for r in summary_rows]
        total_blocks = len(summary_rows)
        seen_blocks = sum(1 for s in statuses if s in ("seen", "completed"))
        completed_blocks = sum(1 for s in statuses if s == "completed")
        last_seen_block_id = next(
            (r[0] for r in reversed(summary_rows) if r[1]),
            None,
        )
        completed = all(s == "completed" for s in statuses)

    return {
        "stored_status": stored_status,
        "progress_summary": {
            "total_blocks": total_blocks,
            "seen_blocks": seen_blocks,
            "completed_blocks": completed_blocks,
            "last_seen_block_id": last_seen_block_id,
            "completed": completed,
        }
    }
