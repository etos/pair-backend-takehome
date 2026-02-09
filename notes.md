# Implementation Notes

## Summary

Completed implementation of the PAIR take-home exercise with the following components:
- **GET** `/tenants/{tenant_id}/users/{user_id}/lessons/{lesson_id}` - Retrieve assembled lesson content with variant selection and user progress
- **PUT** `/tenants/{tenant_id}/users/{user_id}/lessons/{lesson_id}/progress` - Upsert progress for a single block (idempotent, monotonic)

## Key Implementation Decisions

### 1. Variant Selection Strategy

Used PostgreSQL's `LATERAL` join with `ORDER BY tenant_id NULLS LAST` to elegantly select the correct variant per block:
- If a tenant-specific variant exists (`tenant_id = X`), it's selected first
- Otherwise, the default variant (`tenant_id IS NULL`) is used

This approach handles variant selection in a single query without application-level logic.

### 2. Monotonic Progress Constraint

Implemented in the `ON CONFLICT` clause using a `CASE` expression:
```sql
ON CONFLICT (user_id, lesson_id, block_id)
DO UPDATE SET
    status = CASE
        WHEN user_block_progress.status = 'completed' THEN 'completed'
        ELSE EXCLUDED.status
    END
```

This ensures:
- `seen` can upgrade to `completed`
- `completed` cannot downgrade to `seen`
- Idempotent behavior for repeated requests

### 3. Tenant Isolation

All queries validate the tenant relationship chain:
- User must belong to the specified tenant
- Lesson must belong to the specified tenant
- Cross-tenant access returns 404 (not 403) to avoid leaking existence information

### 4. Error Handling

- **404**: Tenant/user/lesson not found OR relationship mismatch
- **400**: Block not part of the lesson
- **422**: Invalid request body (handled by Pydantic validation)

### 5. Progress Summary Calculation

`last_seen_block_id` is determined by iterating blocks in reverse position order and finding the last one with any progress status. This represents the furthest point the user has reached in the lesson.

`completed` is `True` only when ALL blocks have status `completed`.

## Files Modified

1. **app/src/api/v1/lessons.py**
   - Added `ProgressUpsertRequest` and `ProgressUpsertResponse` models
   - Added PUT endpoint for progress upsert
   - Fixed path parameters to use `int` type (matching OpenAPI spec)

2. **app/src/services/lessons.py**
   - Fixed type annotations (`str` → `int` for IDs)
   - Fixed `lesson.id` to return int instead of str
   - Fixed `last_seen_block_id` to return int instead of str
   - Added `upsert_progress()` function with full validation and monotonic constraint

3. **app/tests/test_lessons_api.py** (new)
   - Comprehensive integration tests for both endpoints
   - Tests for success cases, error cases, tenant isolation, and monotonic behavior

## Running Tests

```bash
# Start the database
docker-compose up -d db

# Run tests
cd app && uv run pytest tests/ -v
```

## Potential Improvements (Out of Scope)

1. **Database Connection Pooling**: Currently creates a new engine per request. Should use a shared connection pool.

2. **Transaction Management**: Could wrap validation + upsert in a single transaction for stronger consistency.

3. **Caching**: Lesson structure rarely changes; could cache the block list per lesson.

4. **Batch Progress Updates**: Current API allows one block at a time. A batch endpoint could reduce round trips.

5. **Pagination**: For lessons with many blocks, could paginate the blocks array.

## Time Spent

~45 minutes
