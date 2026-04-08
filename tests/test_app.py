import pytest
from fastapi.testclient import TestClient
import src.app as app_module
from urllib.parse import quote
import copy

client = TestClient(app_module.app)

# Deep copy initial activities for reset
original_activities = copy.deepcopy(app_module.activities)

@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to initial state before each test"""
    app_module.activities = copy.deepcopy(original_activities)


def test_root_redirect():
    """Test that root redirects to static index"""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities():
    """Test getting all activities"""
    response = client.get("/activities")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert len(data) > 0
    # Check structure of one activity
    activity = data["Chess Club"]
    assert "description" in activity
    assert "schedule" in activity
    assert "max_participants" in activity
    assert "participants" in activity
    assert isinstance(activity["participants"], list)


@pytest.mark.parametrize("activity_name,email", [
    ("Chess Club", "test1@mergington.edu"),
    ("Programming Class", "test2@mergington.edu"),
])
def test_signup_success(activity_name, email):
    """Test successful signup"""
    encoded_name = activity_name.replace(" ", "%20")
    response = client.post(f"/activities/{encoded_name}/signup?email={email}")
    assert response.status_code == 200
    result = response.json()
    assert "Signed up" in result["message"]
    assert email in result["message"]

    # Verify added to participants
    response2 = client.get("/activities")
    data = response2.json()
    assert email in data[activity_name]["participants"]


def test_signup_activity_not_found():
    """Test signup for non-existent activity"""
    response = client.post("/activities/NonExistent/signup?email=test@test.com")
    assert response.status_code == 404
    result = response.json()
    assert result["detail"] == "Activity not found"


def test_signup_duplicate():
    """Test signing up twice for same activity"""
    email = "duplicate@test.com"
    activity = "Chess Club"
    encoded_name = activity.replace(" ", "%20")

    # First signup
    client.post(f"/activities/{encoded_name}/signup?email={email}")

    # Second signup should fail
    response = client.post(f"/activities/{encoded_name}/signup?email={email}")
    assert response.status_code == 400
    result = response.json()
    assert "already signed up" in result["detail"]


def test_signup_activity_full():
    """Test signing up for full activity"""
    activity = "Chess Club"
    encoded_name = activity.replace(" ", "%20")
    max_part = original_activities[activity]["max_participants"]
    initial_count = len(original_activities[activity]["participants"])

    # Fill the activity
    for i in range(max_part - initial_count):
        client.post(f"/activities/{encoded_name}/signup?email=fill{i}@test.com")

    # Next signup should fail
    response = client.post(f"/activities/{encoded_name}/signup?email=overflow@test.com")
    assert response.status_code == 400
    result = response.json()
    assert result["detail"] == "Activity is full"


def test_remove_participant_success():
    """Test successful participant removal"""
    email = "remove@test.com"
    activity = "Chess Club"
    encoded_name = activity.replace(" ", "%20")
    encoded_email = quote(email)

    # First add the participant
    post_response = client.post(f"/activities/{encoded_name}/signup?email={email}")
    assert post_response.status_code == 200

    # Verify added
    get_response = client.get("/activities")
    data = get_response.json()
    assert email in data[activity]["participants"]

    # Now remove
    response = client.delete(f"/activities/{encoded_name}/participants/{encoded_email}")
    assert response.status_code == 200
    result = response.json()
    assert "Removed" in result["message"]
    assert email in result["message"]

    # Verify removed
    response2 = client.get("/activities")
    data = response2.json()
    assert email not in data[activity]["participants"]


def test_remove_activity_not_found():
    """Test removing from non-existent activity"""
    response = client.delete("/activities/NonExistent/participants/test@test.com")
    assert response.status_code == 404
    result = response.json()
    assert result["detail"] == "Activity not found"


def test_remove_participant_not_found():
    """Test removing non-existent participant"""
    response = client.delete(f"/activities/Chess%20Club/participants/{quote('nonexistent@test.com')}")
    assert response.status_code == 404
    result = response.json()
    assert result["detail"] == "Participant not found"