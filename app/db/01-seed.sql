-- Seed data for the take-home exercise.
-- This creates 2 tenants, 3 users, 2 lessons, and a handful of blocks/variants/progress.

BEGIN;

INSERT INTO tenants (id, name) VALUES
  (1, 'Acme Corp'),
  (2, 'Globex Inc');

INSERT INTO users (id, tenant_id, email) VALUES
  (10, 1, 'alice@acme.example'),
  (11, 1, 'bob@acme.example'),
  (20, 2, 'charlie@globex.example');

INSERT INTO lessons (id, tenant_id, slug, title) VALUES
  (100, 1, 'ai-basics', 'AI Basics'),
  (200, 2, 'ai-basics', 'AI Basics (Globex)');

INSERT INTO blocks (id, block_type) VALUES
  (200, 'markdown'),
  (201, 'quiz'),
  (202, 'markdown');

-- Lesson 100 (Acme): 200 -> 201 -> 202
INSERT INTO lesson_blocks (lesson_id, block_id, position) VALUES
  (100, 200, 1),
  (100, 201, 2),
  (100, 202, 3);

-- Lesson 200 (Globex): 200 -> 202 -> 201 (different order to force correct ordering)
INSERT INTO lesson_blocks (lesson_id, block_id, position) VALUES
  (200, 200, 1),
  (200, 202, 2),
  (200, 201, 3);

-- Default variants (tenant_id NULL)
INSERT INTO block_variants (id, block_id, tenant_id, data) VALUES
  (1000, 200, NULL, '{"markdown": "Welcome to **AI Basics**. This is the default intro."}'),
  (1001, 201, NULL, '{"question": "In one sentence, what is a neural network?"}'),
  (1002, 202, NULL, '{"markdown": "Summary: You have completed the basics. (Default summary)"}');

-- Tenant-specific overrides
INSERT INTO block_variants (id, block_id, tenant_id, data) VALUES
  (1100, 200, 1, '{"markdown": "Welcome Acme team — this intro is customised for your organisation."}'),
  (1200, 202, 2, '{"markdown": "Globex summary: remember to follow internal AI policy when applying these ideas."}');

-- Initial progress for Alice in Acme lesson 100
INSERT INTO user_block_progress (user_id, lesson_id, block_id, status) VALUES
  (10, 100, 200, 'completed'),
  (10, 100, 201, 'seen');

COMMIT;
