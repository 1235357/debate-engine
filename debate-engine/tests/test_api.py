import pytest
from fastapi.testclient import TestClient
from debate_engine.api import app

client = TestClient(app)


def test_health_check():
    """测试健康检查"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_quick_critique():
    """测试快速批评 API"""
    response = client.post(
        "/v1/quick-critique",
        json={
            "content": "def vulnerable_function(user_input):\n    query = f\"SELECT * FROM users WHERE username = '{user_input}'\"\n    return execute_query(query)",
            "task_type": "CODE_REVIEW",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "final_conclusion" in data
    assert "total_critiques" in data
    assert data["total_critiques"] >= 2
