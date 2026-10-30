import sqlite3
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app import audit, main


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Each test receives an isolated temporary audit database."""

    monkeypatch.setattr(
        audit,
        "AUDIT_PATH",
        str(tmp_path / "audit.sqlite"),
    )

    # Opening TestClient as a context manager runs the app lifespan.
    with TestClient(main.app) as test_client:
        yield test_client


def authenticated_headers():
    return {
        "X-Gateway-Key": main.API_KEY,
    }


def test_valid_query_returns_aggregate(client, monkeypatch):
    # Replace real PostgreSQL execution with a controlled test result.
    execute = Mock(return_value=20)
    monkeypatch.setattr(main, "execute_plan", execute)

    response = client.post(
        "/query",
        headers=authenticated_headers(),
        json={
            "sql": (
                "SELECT COUNT(*) "
                "FROM public.patient_dimension"
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["rows"] == [
        {"patient_count": 20}
    ]
    execute.assert_called_once()


def test_invalid_query_never_reaches_database(client, monkeypatch):
    execute = Mock()
    monkeypatch.setattr(main, "execute_plan", execute)

    response = client.post(
        "/query",
        headers=authenticated_headers(),
        json={
            "sql": "DELETE FROM public.patient_dimension"
        },
    )

    assert response.status_code == 422
    execute.assert_not_called()


def test_missing_key_never_reaches_database(client, monkeypatch):
    execute = Mock()
    monkeypatch.setattr(main, "execute_plan", execute)

    response = client.post(
        "/query",
        json={
            "sql": (
                "SELECT COUNT(*) "
                "FROM public.patient_dimension"
            )
        },
    )

    assert response.status_code == 401
    execute.assert_not_called()


def test_small_count_is_not_released(client, monkeypatch):
    monkeypatch.setattr(
        main,
        "execute_plan",
        Mock(return_value=3),
    )

    response = client.post(
        "/query",
        headers=authenticated_headers(),
        json={
            "sql": (
                "SELECT COUNT(*) "
                "FROM public.patient_dimension"
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "suppressed"
    assert response.json()["rows"] == [
        {"patient_count": None}
    ]


def test_audit_failure_blocks_execution(client, monkeypatch):
    execute = Mock()
    monkeypatch.setattr(main, "execute_plan", execute)

    monkeypatch.setattr(
        main,
        "record_event",
        Mock(
            side_effect=sqlite3.OperationalError(
                "Simulated storage failure"
            )
        ),
    )

    response = client.post(
        "/query",
        headers=authenticated_headers(),
        json={
            "sql": (
                "SELECT COUNT(*) "
                "FROM public.patient_dimension"
            )
        },
    )

    assert response.status_code == 503
    execute.assert_not_called()


def test_final_audit_failure_does_not_release_result(
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        main,
        "execute_plan",
        Mock(return_value=20),
    )

    # First audit event succeeds.
    # Final audit event fails after database execution.
    monkeypatch.setattr(
        main,
        "record_event",
        Mock(
            side_effect=[
                None,
                sqlite3.OperationalError(
                    "Simulated final write failure"
                ),
            ]
        ),
    )

    response = client.post(
        "/query",
        headers=authenticated_headers(),
        json={
            "sql": (
                "SELECT COUNT(*) "
                "FROM public.patient_dimension"
            )
        },
    )

    assert response.status_code == 503
    assert "rows" not in response.json()