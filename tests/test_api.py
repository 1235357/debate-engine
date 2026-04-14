"""FastAPI integration tests for DebateEngine."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from debate_engine.api.server import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.mark.asyncio
async def test_health_endpoint(client: TestClient):
    """Test the health endpoint."""
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "version": "0.1.0"}


@pytest.mark.asyncio
async def test_health_endpoint_compat(client: TestClient):
    """Test the compatibility health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_quick_critique_endpoint(client: TestClient):
    """Test the quick critique endpoint."""
    # Mock the QuickCritiqueEngine
    with patch("debate_engine.api.server.get_quick_engine") as mock_get_engine:
        # Create a mock engine
        mock_engine = AsyncMock()
        # Create a mock result using the actual ConsensusSchema class
        from debate_engine.schemas import ConsensusSchema, DebateMetadata
        from debate_engine.schemas.enums import ProviderMode, TaskType, TerminationReason

        # Create a proper ConsensusSchema object
        mock_result = ConsensusSchema(
            final_conclusion="Test conclusion",
            consensus_confidence=0.85,
            critiques_summary=[],
            debate_metadata=DebateMetadata(
                request_id="test-request-id",
                task_type=TaskType.CODE_REVIEW,
                provider_mode=ProviderMode.STABLE,
                rounds_completed=1,
                total_cost_usd=0.05,
                total_latency_ms=1000.0,
                models_used=["test-model"],
                quorum_achieved=True,
                termination_reason=TerminationReason.COMPLETED,
                parse_attempts_total=0,
            ),
            adopted_contributions={},
            rejected_positions=[],
            remaining_disagreements=[],
            disagreement_confirmation="No disagreements found",
            preserved_minority_opinions=[],
            partial_return=False,
        )
        # Make the mock return the object
        mock_engine.critique.return_value = mock_result
        mock_get_engine.return_value = mock_engine

        # Test the endpoint
        response = client.post(
            "/v1/quick-critique",
            json={"content": "def hello(): print('hello')", "task_type": "CODE_REVIEW"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["final_conclusion"] == "Test conclusion"
        assert data["consensus_confidence"] == 0.85


@pytest.mark.asyncio
async def test_debate_endpoint(client: TestClient):
    """Test the debate endpoint."""
    # Mock the DebateOrchestrator
    with patch("debate_engine.api.server.get_debate_orchestrator") as mock_get_orchestrator:
        # Create a mock orchestrator
        mock_orchestrator = AsyncMock()
        mock_orchestrator.submit.return_value = "test-job-id"
        mock_get_orchestrator.return_value = mock_orchestrator

        # Test the endpoint
        response = client.post(
            "/v1/debate",
            json={"content": "def hello(): print('hello')", "task_type": "CODE_REVIEW"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "test-job-id"
        assert data["status"] == "PENDING"


@pytest.mark.asyncio
async def test_chat_endpoint(client: TestClient):
    """Test the chat endpoint."""
    # Mock the QuickCritiqueEngine
    with patch("debate_engine.api.server.get_quick_engine") as mock_get_engine:
        # Create a mock engine
        mock_engine = AsyncMock()
        # Create a mock result using SimpleNamespace to simulate object with attributes
        from types import SimpleNamespace

        # Create mock objects with proper attributes
        mock_task_type = SimpleNamespace(value="CODE_REVIEW")
        mock_provider_mode = SimpleNamespace(value="STABLE")
        mock_termination_reason = SimpleNamespace(value="COMPLETED")

        mock_debate_metadata = SimpleNamespace(
            request_id="test-chat-request-id",
            task_type=mock_task_type,
            provider_mode=mock_provider_mode,
            rounds_completed=1,
            total_cost_usd=0.08,
            total_latency_ms=1500.0,
            models_used=["test-model"],
            quorum_achieved=True,
            termination_reason=mock_termination_reason,
            parse_attempts_total=0,
        )

        mock_result = SimpleNamespace(
            final_conclusion="Test chat conclusion",
            consensus_confidence=0.9,
            critiques_summary=[],
            debate_metadata=mock_debate_metadata,
            adopted_contributions={},
            rejected_positions=[],
            remaining_disagreements=[],
            disagreement_confirmation="",
            preserved_minority_opinions=[],
            partial_return=False,
        )
        # Make the mock return the object
        mock_engine.critique.return_value = mock_result
        mock_get_engine.return_value = mock_engine

        # Test the endpoint
        response = client.post(
            "/api/chat",
            json={
                "messages": [{"role": "user", "content": "def hello(): print('hello')"}],
                "model": "test-model",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["final_conclusion"] == "Test chat conclusion"
        assert data["consensus_confidence"] == 0.9


@pytest.mark.asyncio
async def test_quick_critique_api_endpoint(client: TestClient):
    """Test the quick critique API endpoint."""
    # Mock the QuickCritiqueEngine
    with patch("debate_engine.api.server.get_quick_engine") as mock_get_engine:
        # Create a mock engine
        mock_engine = AsyncMock()
        # Create a mock result using SimpleNamespace to simulate object with attributes
        from types import SimpleNamespace

        # Create mock objects with proper attributes
        mock_task_type = SimpleNamespace(value="CODE_REVIEW")
        mock_provider_mode = SimpleNamespace(value="STABLE")
        mock_termination_reason = SimpleNamespace(value="COMPLETED")

        mock_debate_metadata = SimpleNamespace(
            request_id="test-api-request-id",
            task_type=mock_task_type,
            provider_mode=mock_provider_mode,
            rounds_completed=1,
            total_cost_usd=0.06,
            total_latency_ms=1200.0,
            models_used=["test-model"],
            quorum_achieved=True,
            termination_reason=mock_termination_reason,
            parse_attempts_total=0,
        )

        mock_result = SimpleNamespace(
            final_conclusion="Test API conclusion",
            consensus_confidence=0.8,
            critiques_summary=[],
            debate_metadata=mock_debate_metadata,
            adopted_contributions={},
            rejected_positions=[],
            remaining_disagreements=[],
            disagreement_confirmation="",
            preserved_minority_opinions=[],
            partial_return=False,
        )
        # Make the mock return the object
        mock_engine.critique.return_value = mock_result
        mock_get_engine.return_value = mock_engine

        # Test the endpoint
        response = client.post(
            "/api/quick-critique",
            json={"content": "def hello(): print('hello')", "task_type": "CODE_REVIEW"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["final_conclusion"] == "Test API conclusion"
        assert data["consensus_confidence"] == 0.8
