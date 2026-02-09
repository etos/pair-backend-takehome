import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from src.conf import AppConfig

conf = AppConfig()
logging.basicConfig(level=conf.LOG_LEVEL)



async def get_lesson(tenant_id: str, user_id: str, lesson_id: str) -> dict | None:
    """
    Retrieve lesson.

    TODO: move db init to a central module
    TODO: remove wildcards in SQL
    TODO: add unit tests / integration tests
    """
    db = create_async_engine(conf.POSTGRES_URL)
    params = {"tenant_id": int(tenant_id), "user_id": int(user_id), "lesson_id": int(lesson_id)}

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
            "id": str(rows[0]["lesson_id"]),       # from first row only
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
                    "progress": r["progress_status"],
                },
                "user_progress": r["progress_status"],
            }
            for r in rows                          # one per block
        ],
        "progress_summary": {
            "total_blocks": len(rows),
            "seen_blocks": sum(1 for s in statuses if s in ("seen", "completed")),
            "completed_blocks": sum(1 for s in statuses if s == "completed"),
            "last_seen_block_id": next(
                (str(r["block_id"]) for r in reversed(rows) if r["progress_status"]),
                None,
            ),
            "completed": "true" if all(s == "completed" for s in statuses) else "false",
        }

    }

    return data
