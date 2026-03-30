import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Provide a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to a clean state before each test"""
    # Store original state
    original_activities = {
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 2,
            "participants": ["michael@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": []
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 3,
            "participants": ["john@mergington.edu", "olivia@mergington.edu"]
        }
    }
    
    # Clear current activities
    activities.clear()
    
    # Populate with test data
    activities.update(original_activities)
    
    yield
    
    # Cleanup after test
    activities.clear()
    activities.update(original_activities)


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Should return all activities with correct structure"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
        
        # Verify structure
        activity = data["Chess Club"]
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity
    
    def test_get_activities_shows_correct_participant_count(self, client):
        """Should show accurate participant counts"""
        response = client.get("/activities")
        data = response.json()
        
        assert len(data["Chess Club"]["participants"]) == 1
        assert len(data["Gym Class"]["participants"]) == 2
        assert len(data["Programming Class"]["participants"]) == 0


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_successful(self, client):
        """Should successfully sign up a student"""
        response = client.post(
            "/activities/Programming%20Class/signup",
            params={"email": "alice@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Signed up alice@mergington.edu for Programming Class" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        assert "alice@mergington.edu" in activities_response.json()["Programming Class"]["participants"]
    
    def test_signup_activity_not_found(self, client):
        """Should return 404 if activity doesn't exist"""
        response = client.post(
            "/activities/Nonexistent%20Club/signup",
            params={"email": "alice@mergington.edu"}
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"
    
    def test_signup_already_signed_up(self, client):
        """Should return 400 if student is already signed up"""
        response = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "michael@mergington.edu"}
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Student already signed up"
    
    def test_signup_activity_at_capacity(self, client):
        """Should return 400 if activity is at maximum capacity"""
        # Chess Club has max 2 participants, 1 already signed up
        # Sign up one more to reach capacity
        response = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "bob@mergington.edu"}
        )
        assert response.status_code == 200
        
        # Try to sign up another - should fail
        response = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "charlie@mergington.edu"}
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Activity is at maximum capacity"
    
    def test_signup_multiple_students(self, client):
        """Should allow multiple different students to sign up"""
        # Programming Class has space for 20
        response1 = client.post(
            "/activities/Programming%20Class/signup",
            params={"email": "alice@mergington.edu"}
        )
        response2 = client.post(
            "/activities/Programming%20Class/signup",
            params={"email": "bob@mergington.edu"}
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        activities_response = client.get("/activities")
        participants = activities_response.json()["Programming Class"]["participants"]
        assert "alice@mergington.edu" in participants
        assert "bob@mergington.edu" in participants


class TestRemoveParticipant:
    """Tests for DELETE /activities/{activity_name}/participants/{email} endpoint"""
    
    def test_remove_participant_successful(self, client):
        """Should successfully remove a participant"""
        response = client.delete(
            "/activities/Chess%20Club/participants/michael%40mergington.edu"
        )
        assert response.status_code == 200
        assert "Removed michael@mergington.edu from Chess Club" in response.json()["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        assert "michael@mergington.edu" not in activities_response.json()["Chess Club"]["participants"]
    
    def test_remove_activity_not_found(self, client):
        """Should return 404 if activity doesn't exist"""
        response = client.delete(
            "/activities/Nonexistent%20Club/participants/alice%40mergington.edu"
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"
    
    def test_remove_participant_not_found(self, client):
        """Should return 404 if participant is not in activity"""
        response = client.delete(
            "/activities/Chess%20Club/participants/alice%40mergington.edu"
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Participant not found in this activity"
    
    def test_remove_multiple_participants(self, client):
        """Should allow removing multiple participants"""
        # Gym Class has 2 participants
        response1 = client.delete(
            "/activities/Gym%20Class/participants/john%40mergington.edu"
        )
        response2 = client.delete(
            "/activities/Gym%20Class/participants/olivia%40mergington.edu"
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        activities_response = client.get("/activities")
        participants = activities_response.json()["Gym Class"]["participants"]
        assert len(participants) == 0


class TestSignupAfterRemoval:
    """Integration tests for signup after removal"""
    
    def test_signup_after_removal_in_full_activity(self, client):
        """Should allow signup after removal even when activity was full"""
        # Chess Club is max 2, has 1 participant
        # Sign up charlie to reach capacity
        client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "charlie@mergington.edu"}
        )
        
        # Verify at capacity
        response = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "bob@mergington.edu"}
        )
        assert response.status_code == 400  # at capacity
        
        # Remove michael
        client.delete(
            "/activities/Chess%20Club/participants/michael%40mergington.edu"
        )
        
        # Now should be able to sign up bob
        response = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "bob@mergington.edu"}
        )
        assert response.status_code == 200
