"""Supabase authentication service managing user sessions and DEMO_MODE fallback."""

from typing import Optional, Dict, Any
from config.settings import Settings, get_settings
from services.supabase_service import SupabaseService, supabase_service
from utils.logger import logger
from utils.exceptions import ServiceError

DEMO_USER_ID = "00000000-0000-0000-0000-000000000001"
DEMO_USER_EMAIL = "demo.traveler@example.com"


class AuthService:
    """Manages authentication lifecycles using Supabase Auth with safe DEMO_MODE support."""

    def __init__(
        self,
        supabase_svc: Optional[SupabaseService] = None,
        settings: Optional[Settings] = None,
    ):
        self.settings = settings or get_settings()
        self.supabase_svc = supabase_svc or supabase_service

    @property
    def is_configured(self) -> bool:
        """Check whether Supabase Auth is configured."""
        return self.supabase_svc.is_configured

    @property
    def is_demo_mode(self) -> bool:
        """Check whether running in DEMO_MODE."""
        return self.settings.demo_mode

    def get_current_user(self, session_state: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Retrieve current authenticated user from session state or default demo identity.

        Args:
            session_state: Streamlit session state dictionary or dict-like object.

        Returns:
            Dict containing user metadata (id, email, is_demo, etc.), or None if unauthenticated.
        """
        if session_state and "auth_user" in session_state and session_state["auth_user"] is not None:
            return session_state["auth_user"]

        # Default fallback in DEMO_MODE
        if self.is_demo_mode or not self.is_configured:
            return {
                "id": DEMO_USER_ID,
                "email": DEMO_USER_EMAIL,
                "full_name": "Demo Traveler",
                "is_demo": True,
            }

        return None

    def sign_in(self, email: str, password: str, session_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Authenticate user with email and password via Supabase Auth.

        Args:
            email: User email address.
            password: User password.
            session_state: Streamlit session state dictionary to populate upon success.

        Returns:
            User dictionary with id, email, and session metadata.

        Raises:
            ServiceError: If authentication fails.
        """
        if not self.is_configured or self.is_demo_mode:
            logger.info("Sign-in simulated in DEMO_MODE.")
            user_data = {
                "id": DEMO_USER_ID,
                "email": email or DEMO_USER_EMAIL,
                "full_name": "Demo Traveler",
                "is_demo": True,
            }
            if session_state is not None:
                session_state["auth_user"] = user_data
            return user_data

        client = self.supabase_svc.get_client()
        if not client:
            raise ServiceError("SupabaseAuth", "Supabase client is unavailable.")

        try:
            response = client.auth.sign_in_with_password({
                "email": email.strip(),
                "password": password,
            })
            if not response or not response.user:
                raise ServiceError("SupabaseAuth", "Invalid email or password.")

            user_data = {
                "id": str(response.user.id),
                "email": response.user.email,
                "full_name": response.user.user_metadata.get("full_name", response.user.email),
                "is_demo": False,
                "access_token": response.session.access_token if response.session else None,
            }

            if session_state is not None:
                session_state["auth_user"] = user_data

            logger.info(f"User authenticated successfully: {user_data['email']}")
            return user_data
        except Exception as e:
            logger.warning(f"Authentication failed for user {email}: {str(e)}")
            raise ServiceError("SupabaseAuth", f"Sign in failed: {str(e)}") from e

    def sign_up(self, email: str, password: str, full_name: Optional[str] = None) -> Dict[str, Any]:
        """Register a new user account with Supabase Auth.

        Args:
            email: User email address.
            password: User password.
            full_name: Optional display name.

        Returns:
            Registered user dictionary.

        Raises:
            ServiceError: If sign up fails.
        """
        if not self.is_configured or self.is_demo_mode:
            logger.info("Sign-up simulated in DEMO_MODE.")
            return {
                "id": DEMO_USER_ID,
                "email": email or DEMO_USER_EMAIL,
                "full_name": full_name or "Demo Traveler",
                "is_demo": True,
            }

        client = self.supabase_svc.get_client()
        if not client:
            raise ServiceError("SupabaseAuth", "Supabase client is unavailable.")

        try:
            options = {}
            if full_name:
                options["data"] = {"full_name": full_name}

            response = client.auth.sign_up({
                "email": email.strip(),
                "password": password,
                "options": options,
            })
            if not response or not response.user:
                raise ServiceError("SupabaseAuth", "User registration failed.")

            logger.info(f"New user registered: {response.user.email}")
            return {
                "id": str(response.user.id),
                "email": response.user.email,
                "full_name": full_name or response.user.email,
                "is_demo": False,
            }
        except Exception as e:
            logger.warning(f"Registration failed for {email}: {str(e)}")
            raise ServiceError("SupabaseAuth", f"Sign up failed: {str(e)}") from e

    def sign_out(self, session_state: Optional[Dict[str, Any]] = None) -> None:
        """Sign out current user and clear local session state."""
        if self.is_configured and not self.is_demo_mode:
            client = self.supabase_svc.get_client()
            if client:
                try:
                    client.auth.sign_out()
                except Exception as e:
                    logger.warning(f"Error signing out from Supabase: {e}")

        if session_state is not None:
            session_state["auth_user"] = None

        logger.info("User signed out successfully.")


# Global singleton instance
auth_service = AuthService()
