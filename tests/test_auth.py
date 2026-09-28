"""Unit tests for authentication service and session identity."""

from services.auth_service import AuthService, DEMO_USER_ID, DEMO_USER_EMAIL


def test_auth_service_demo_mode_defaults():
    """Verify default demo traveler identity in DEMO_MODE."""
    auth = AuthService()
    session = {}

    user = auth.get_current_user(session)
    assert user is not None
    assert user["id"] == DEMO_USER_ID
    assert user["email"] == DEMO_USER_EMAIL
    assert user["is_demo"] is True


def test_auth_service_demo_sign_in_and_out():
    """Verify mock sign-in and sign-out populate and clear session state."""
    auth = AuthService()
    session = {}

    # Sign in
    signed_in = auth.sign_in("traveler@test.com", "password123", session_state=session)
    assert signed_in["email"] == "traveler@test.com"
    assert session["auth_user"]["email"] == "traveler@test.com"

    # User retrieval reflects session
    curr = auth.get_current_user(session)
    assert curr["email"] == "traveler@test.com"

    # Sign out
    auth.sign_out(session_state=session)
    assert session["auth_user"] is None


def test_auth_service_demo_sign_up():
    """Verify mock sign-up produces valid user structure."""
    auth = AuthService()
    res = auth.sign_up("new.user@test.com", "secretpass", full_name="Alice Explorer")
    assert res["id"] is not None
    assert res["email"] == "new.user@test.com"
    assert res["full_name"] == "Alice Explorer"
    assert res["is_demo"] is True
