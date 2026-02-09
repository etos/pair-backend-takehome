"""
Integration tests for the lessons API endpoints.

These tests require a running PostgreSQL database with seed data.
Run with: cd app && uv run pytest tests/
"""
import pytest
from fastapi.testclient import TestClient
from src.main import app


client = TestClient(app)


class TestGetLesson:
    """Tests for GET /tenants/{tenant_id}/users/{user_id}/lessons/{lesson_id}"""

    def test_get_lesson_success(self):
        """Should return lesson with blocks and progress for valid tenant/user/lesson."""
        response = client.get("/api/v1/tenants/1/users/10/lessons/100")
        assert response.status_code == 200

        data = response.json()
        assert "lesson" in data
        assert "blocks" in data
        assert "progress_summary" in data

        # Verify lesson structure
        assert data["lesson"]["id"] == 100
        assert data["lesson"]["slug"] == "ai-basics"
        assert data["lesson"]["title"] == "AI Basics"

        # Verify blocks are ordered by position
        assert len(data["blocks"]) == 3
        positions = [b["position"] for b in data["blocks"]]
        assert positions == [1, 2, 3]

        # Verify block structure
        first_block = data["blocks"][0]
        assert first_block["id"] == 200
        assert first_block["type"] == "markdown"
        assert "variant" in first_block
        assert "id" in first_block["variant"]
        assert "tenant_id" in first_block["variant"]
        assert "data" in first_block["variant"]

    def test_get_lesson_tenant_override_variant(self):
        """Should return tenant-specific variant when available."""
        response = client.get("/api/v1/tenants/1/users/10/lessons/100")
        assert response.status_code == 200

        data = response.json()
        # Block 200 should use tenant 1's override (variant id 1100)
        block_200 = data["blocks"][0]
        assert block_200["id"] == 200
        assert block_200["variant"]["id"] == 1100
        assert block_200["variant"]["tenant_id"] == 1

    def test_get_lesson_default_variant(self):
        """Should return default variant when no tenant override exists."""
        response = client.get("/api/v1/tenants/1/users/10/lessons/100")
        assert response.status_code == 200

        data = response.json()
        # Block 201 and 202 should use default variants (tenant_id = null)
        block_201 = data["blocks"][1]
        assert block_201["id"] == 201
        assert block_201["variant"]["tenant_id"] is None

    def test_get_lesson_progress_summary(self):
        """Should return correct progress summary based on seed data."""
        response = client.get("/api/v1/tenants/1/users/10/lessons/100")
        assert response.status_code == 200

        data = response.json()
        summary = data["progress_summary"]

        assert summary["total_blocks"] == 3
        # Block 200 is completed, block 201 is seen
        assert summary["seen_blocks"] == 2
        assert summary["completed_blocks"] == 1
        assert summary["last_seen_block_id"] == 201
        assert summary["completed"] is False

    def test_get_lesson_user_progress_on_blocks(self):
        """Should return correct user_progress for each block."""
        response = client.get("/api/v1/tenants/1/users/10/lessons/100")
        assert response.status_code == 200

        data = response.json()
        blocks = data["blocks"]

        # Based on seed data: block 200=completed, 201=seen, 202=null
        assert blocks[0]["user_progress"] == "completed"
        assert blocks[1]["user_progress"] == "seen"
        assert blocks[2]["user_progress"] is None

    def test_get_lesson_not_found_invalid_tenant(self):
        """Should return 404 for non-existent tenant."""
        response = client.get("/api/v1/tenants/999/users/10/lessons/100")
        assert response.status_code == 404

    def test_get_lesson_not_found_invalid_user(self):
        """Should return 404 for non-existent user."""
        response = client.get("/api/v1/tenants/1/users/999/lessons/100")
        assert response.status_code == 404

    def test_get_lesson_not_found_invalid_lesson(self):
        """Should return 404 for non-existent lesson."""
        response = client.get("/api/v1/tenants/1/users/10/lessons/999")
        assert response.status_code == 404

    def test_get_lesson_cross_tenant_user_not_allowed(self):
        """Should return 404 when user doesn't belong to tenant."""
        # User 20 belongs to tenant 2, not tenant 1
        response = client.get("/api/v1/tenants/1/users/20/lessons/100")
        assert response.status_code == 404

    def test_get_lesson_cross_tenant_lesson_not_allowed(self):
        """Should return 404 when lesson doesn't belong to tenant."""
        # Lesson 200 belongs to tenant 2, not tenant 1
        response = client.get("/api/v1/tenants/1/users/10/lessons/200")
        assert response.status_code == 404

    def test_get_lesson_globex_different_block_order(self):
        """Should return blocks in correct order for Globex (different from Acme)."""
        response = client.get("/api/v1/tenants/2/users/20/lessons/200")
        assert response.status_code == 200

        data = response.json()
        # Globex lesson has different block order: 200 -> 202 -> 201
        block_ids = [b["id"] for b in data["blocks"]]
        assert block_ids == [200, 202, 201]


class TestUpsertProgress:
    """Tests for PUT /tenants/{tenant_id}/users/{user_id}/lessons/{lesson_id}/progress"""

    def test_upsert_progress_seen_success(self):
        """Should successfully mark a block as seen."""
        response = client.put(
            "/api/v1/tenants/1/users/11/lessons/100/progress",
            json={"block_id": 200, "status": "seen"}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["stored_status"] == "seen"
        assert "progress_summary" in data
        assert data["progress_summary"]["seen_blocks"] >= 1

    def test_upsert_progress_completed_success(self):
        """Should successfully mark a block as completed."""
        response = client.put(
            "/api/v1/tenants/1/users/11/lessons/100/progress",
            json={"block_id": 201, "status": "completed"}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["stored_status"] == "completed"
        assert data["progress_summary"]["completed_blocks"] >= 1

    def test_upsert_progress_idempotent(self):
        """Should be idempotent - same request returns same result."""
        payload = {"block_id": 202, "status": "seen"}

        response1 = client.put(
            "/api/v1/tenants/1/users/11/lessons/100/progress",
            json=payload
        )
        response2 = client.put(
            "/api/v1/tenants/1/users/11/lessons/100/progress",
            json=payload
        )

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json()["stored_status"] == response2.json()["stored_status"]

    def test_upsert_progress_monotonic_no_downgrade(self):
        """Should not downgrade completed to seen (monotonic constraint)."""
        # First mark as completed
        response1 = client.put(
            "/api/v1/tenants/1/users/11/lessons/100/progress",
            json={"block_id": 200, "status": "completed"}
        )
        assert response1.status_code == 200
        assert response1.json()["stored_status"] == "completed"

        # Try to downgrade to seen - should remain completed
        response2 = client.put(
            "/api/v1/tenants/1/users/11/lessons/100/progress",
            json={"block_id": 200, "status": "seen"}
        )
        assert response2.status_code == 200
        assert response2.json()["stored_status"] == "completed"

    def test_upsert_progress_upgrade_seen_to_completed(self):
        """Should allow upgrading from seen to completed."""
        # First mark as seen
        client.put(
            "/api/v1/tenants/2/users/20/lessons/200/progress",
            json={"block_id": 200, "status": "seen"}
        )

        # Then upgrade to completed
        response = client.put(
            "/api/v1/tenants/2/users/20/lessons/200/progress",
            json={"block_id": 200, "status": "completed"}
        )
        assert response.status_code == 200
        assert response.json()["stored_status"] == "completed"

    def test_upsert_progress_block_not_in_lesson(self):
        """Should return 400 when block_id is not part of the lesson."""
        # Block 999 doesn't exist
        response = client.put(
            "/api/v1/tenants/1/users/10/lessons/100/progress",
            json={"block_id": 999, "status": "seen"}
        )
        assert response.status_code == 400

    def test_upsert_progress_invalid_tenant(self):
        """Should return 404 for non-existent tenant."""
        response = client.put(
            "/api/v1/tenants/999/users/10/lessons/100/progress",
            json={"block_id": 200, "status": "seen"}
        )
        assert response.status_code == 404

    def test_upsert_progress_invalid_user(self):
        """Should return 404 for non-existent user."""
        response = client.put(
            "/api/v1/tenants/1/users/999/lessons/100/progress",
            json={"block_id": 200, "status": "seen"}
        )
        assert response.status_code == 404

    def test_upsert_progress_invalid_lesson(self):
        """Should return 404 for non-existent lesson."""
        response = client.put(
            "/api/v1/tenants/1/users/10/lessons/999/progress",
            json={"block_id": 200, "status": "seen"}
        )
        assert response.status_code == 404

    def test_upsert_progress_cross_tenant_not_allowed(self):
        """Should return 404 when user doesn't belong to tenant."""
        # User 20 belongs to tenant 2, not tenant 1
        response = client.put(
            "/api/v1/tenants/1/users/20/lessons/100/progress",
            json={"block_id": 200, "status": "seen"}
        )
        assert response.status_code == 404

    def test_upsert_progress_invalid_status(self):
        """Should return 422 for invalid status value."""
        response = client.put(
            "/api/v1/tenants/1/users/10/lessons/100/progress",
            json={"block_id": 200, "status": "invalid"}
        )
        assert response.status_code == 422

    def test_upsert_progress_missing_block_id(self):
        """Should return 422 for missing block_id."""
        response = client.put(
            "/api/v1/tenants/1/users/10/lessons/100/progress",
            json={"status": "seen"}
        )
        assert response.status_code == 422

    def test_upsert_progress_missing_status(self):
        """Should return 422 for missing status."""
        response = client.put(
            "/api/v1/tenants/1/users/10/lessons/100/progress",
            json={"block_id": 200}
        )
        assert response.status_code == 422

    def test_upsert_progress_returns_updated_summary(self):
        """Should return updated progress summary after upsert."""
        # Mark all blocks as completed for user 11
        for block_id in [200, 201, 202]:
            client.put(
                "/api/v1/tenants/1/users/11/lessons/100/progress",
                json={"block_id": block_id, "status": "completed"}
            )

        # Check the final response
        response = client.put(
            "/api/v1/tenants/1/users/11/lessons/100/progress",
            json={"block_id": 202, "status": "completed"}
        )
        assert response.status_code == 200

        summary = response.json()["progress_summary"]
        assert summary["total_blocks"] == 3
        assert summary["completed_blocks"] == 3
        assert summary["seen_blocks"] == 3
        assert summary["completed"] is True
