from app.core.security import get_password_hash
from app.db.models import User

def test_login_flow(client, session):
    admin = User(
        email="admin@test.com",
        hashed_password=get_password_hash("pass123"),
        is_active=True,
        full_name="Test Admin"
    )
    session.add(admin)
    session.commit()

    response = client.post(
        "/api/auth/token",
        data={"username": "admin@test.com", "password": "pass123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_dashboard_access_denied(client):
    # Tenter d'accéder sans token
    response = client.get("/admin/stats")
    assert response.status_code == 401  # Unauthorized