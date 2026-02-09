# Data model quick reference

This is a simplified “CMS-like” content model.

## tenants
- `id` (int)
- `name`

## users
- `id`
- `tenant_id` → tenants.id
- `email`

## lessons
- `id`
- `tenant_id` → tenants.id
- `slug`, `title`

## blocks
- `id`
- `block_type` (e.g. markdown, quiz)

## lesson_blocks
Ordered list of blocks inside a lesson.
- `(lesson_id, block_id)` primary key
- `position` (1,2,3,...)

## block_variants
Variant content for a block.
- `block_id` → blocks.id
- `tenant_id` nullable:
  - NULL = default variant
  - set = tenant override
- `data` (jsonb)

## user_block_progress
Per-user progress for each block in a lesson.
- `(user_id, lesson_id, block_id)` primary key
- `status` in {seen, completed}
- `updated_at`
