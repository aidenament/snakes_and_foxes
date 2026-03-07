from fastapi.testclient import TestClient

from snakes_and_foxes.app import app

client = TestClient(app)


def test_homepage_renders():
    response = client.get("/")
    assert response.status_code == 200
    assert "Snakes and Foxes" in response.text
    assert "board-canvas" in response.text


def test_new_game_endpoint_returns_state():
    response = client.post(
        "/api/game/new",
        json={"seed": 123, "board": {"circle_count": 6, "nodes_per_circle": 10}},
    )
    payload = response.json()
    assert response.status_code == 200
    assert payload["state"]["seed"] == 123
    assert payload["state"]["phase"] == "waiting_for_roll"


def test_invalid_move_is_rejected():
    state = client.post(
        "/api/game/new",
        json={"seed": 123, "board": {"circle_count": 6, "nodes_per_circle": 10}},
    ).json()["state"]
    response = client.post(
        "/api/game/action",
        json={
            "state": state,
            "action": {"type": "move", "destination": {"circle_index": 5, "node_index": 5}},
        },
    )
    payload = response.json()
    assert response.status_code == 200
    assert payload["result"]["ok"] is False
    assert "only move after rolling" in payload["result"]["message"].lower()
