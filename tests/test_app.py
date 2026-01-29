from fastapi.testclient import TestClient
import pytest

from src.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_get_activities_contains_chess_club(client):
    r = client.get("/activities")
    assert r.status_code == 200
    data = r.json()
    assert "Chess Club" in data
    assert isinstance(data["Chess Club"]["participants"], list)


def test_signup_and_duplicate_and_unregister(client):
    activity = "Chess Club"
    email = "pytest.user@example.com"

    # Ensure email not present initially (remove if exists)
    resp = client.get(f"/activities")
    participants = resp.json()[activity]["participants"]
    if email in participants:
        client.delete(f"/activities/{activity}/participants?email={email}")

    # Sign up
    r = client.post(f"/activities/{activity}/signup?email={email}")
    assert r.status_code == 200
    assert "Signed up" in r.json().get("message", "")

    # Confirm present
    r2 = client.get("/activities")
    assert email in r2.json()[activity]["participants"]

    # Duplicate signup should be rejected
    r3 = client.post(f"/activities/{activity}/signup?email={email}")
    assert r3.status_code == 400

    # Unregister
    r4 = client.delete(f"/activities/{activity}/participants?email={email}")
    assert r4.status_code == 200
    assert "Unregistered" in r4.json().get("message", "")

    # Final confirm
    r5 = client.get("/activities")
    assert email not in r5.json()[activity]["participants"]


def test_unregister_nonexistent_returns_404(client):
    activity = "Chess Club"
    email = "noone@example.com"
    r = client.delete(f"/activities/{activity}/participants?email={email}")
    # If participant not present, API returns 404
    assert r.status_code == 404


def test_signup_nonexistent_activity_returns_404(client):
    r = client.post("/activities/ThisActivityDoesNotExist/signup?email=foo%40example.com")
    assert r.status_code == 404


def test_unregister_nonexistent_activity_returns_404(client):
    r = client.delete("/activities/NoSuchActivity/participants?email=foo%40example.com")
    assert r.status_code == 404


def test_activity_capacity_limit(client):
    # Create a temporary activity with max_participants=1 to test capacity
    activities = client.get('/activities').json()
    # Add a temporary activity to the in-memory store via direct mutation
    # (the app uses a module-level dict)
    from src import app as app_module
    app_module.activities['Tiny Group'] = {
        'description': 'Tiny',
        'schedule': 'Now',
        'max_participants': 1,
        'participants': []
    }

    # First signup should succeed
    r1 = client.post("/activities/Tiny%20Group/signup?email=a%40ex.com")
    assert r1.status_code == 200

    # Second signup should fail due to capacity
    r2 = client.post("/activities/Tiny%20Group/signup?email=b%40ex.com")
    assert r2.status_code == 400

    # Clean up
    del app_module.activities['Tiny Group']


def test_root_redirects_to_static_index(client):
    r = client.get('/', follow_redirects=False)
    # Should redirect to /static/index.html
    assert r.status_code in (301, 302, 307, 308)
    assert '/static/index.html' in r.headers.get('location', '')
