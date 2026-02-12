"""
Tests for the High School Management System API
"""
import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    activities.clear()
    activities.update({
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": ["john@mergington.edu", "olivia@mergington.edu"]
        }
    })


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for the GET /activities endpoint"""
    
    def test_get_all_activities(self, client):
        """Test getting all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
    
    def test_activities_structure(self, client):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)


class TestSignupForActivity:
    """Tests for the POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_for_existing_activity(self, client):
        """Test signing up for an existing activity"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Signed up test@mergington.edu for Chess Club"
        
        # Verify the participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "test@mergington.edu" in activities_data["Chess Club"]["participants"]
    
    def test_signup_for_nonexistent_activity(self, client):
        """Test signing up for a non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Club/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_multiple_signups(self, client):
        """Test multiple students signing up for the same activity"""
        emails = ["student1@mergington.edu", "student2@mergington.edu", "student3@mergington.edu"]
        
        for email in emails:
            response = client.post(
                "/activities/Programming Class/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify all participants were added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        participants = activities_data["Programming Class"]["participants"]
        
        for email in emails:
            assert email in participants
    
    def test_duplicate_signup_rejected(self, client):
        """Test that duplicate signups are rejected with 400 error"""
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        
        # Second signup with same email should fail
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Student already signed up for this activity"
    
    def test_activity_at_capacity_rejected(self, client):
        """Test that signups are rejected when activity is at max capacity"""
        # Fill up Chess Club (max_participants: 12, currently has 2)
        for i in range(10):  # 2 existing + 10 new = 12 (full)
            response = client.post(
                "/activities/Chess Club/signup",
                params={"email": f"student{i}@mergington.edu"}
            )
            assert response.status_code == 200
        
        # Attempt one more signup when activity is full
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "overflow@mergington.edu"}
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Activity is full"


class TestUnregisterFromActivity:
    """Tests for the DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_existing_participant(self, client):
        """Test unregistering an existing participant"""
        response = client.delete(
            "/activities/Chess Club/unregister",
            params={"email": "michael@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Unregistered michael@mergington.edu from Chess Club"
        
        # Verify the participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "michael@mergington.edu" not in activities_data["Chess Club"]["participants"]
    
    def test_unregister_nonexistent_participant(self, client):
        """Test unregistering a participant who is not signed up"""
        response = client.delete(
            "/activities/Chess Club/unregister",
            params={"email": "nonexistent@mergington.edu"}
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Participant not found"
    
    def test_unregister_from_nonexistent_activity(self, client):
        """Test unregistering from a non-existent activity"""
        response = client.delete(
            "/activities/Nonexistent Club/unregister",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_signup_and_unregister_workflow(self, client):
        """Test the complete workflow of signing up and unregistering"""
        email = "workflow@mergington.edu"
        activity = "Gym Class"
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert signup_response.status_code == 200
        
        # Verify signup
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity]["participants"]
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        assert unregister_response.status_code == 200
        
        # Verify unregistration
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data[activity]["participants"]
