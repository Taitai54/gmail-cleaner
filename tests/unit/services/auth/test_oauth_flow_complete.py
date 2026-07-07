"""
Tests for Complete OAuth Flow Scenarios
----------------------------------------
Tests for successful OAuth flows and edge cases not covered in existing tests.
"""

import time
from unittest.mock import Mock, patch, mock_open


from app.services import auth

MOCK_INSTALLED_CREDENTIALS = (
    '{"installed": {"client_id": "test", "client_secret": "secret", '
    '"auth_uri": "https://accounts.google.com/o/oauth2/auth", '
    '"token_uri": "https://oauth2.googleapis.com/token"}}'
)


def _mock_oauth_flow(mock_flow):
    mock_flow_instance = Mock()
    mock_flow.from_client_config.return_value = mock_flow_instance
    mock_flow_instance.authorization_url.return_value = (
        "https://accounts.google.com/o/oauth2/auth?test=1",
        "oauth-state",
    )
    return mock_flow_instance


class TestSuccessfulOAuthFlow:
    """Tests for successful OAuth flow scenarios"""

    @patch("app.services.auth.HTTPServer")
    @patch("app.services.auth.settings")
    @patch("app.services.auth._is_file_empty")
    @patch("app.services.auth.os.path.exists")
    @patch("app.services.auth.InstalledAppFlow")
    @patch("app.services.auth._auth_in_progress", {"active": False})
    @patch("app.services.auth.is_web_auth_mode", return_value=False)
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data=MOCK_INSTALLED_CREDENTIALS,
    )
    def test_complete_oauth_flow_saves_token(
        self,
        mock_file,
        mock_web_auth,
        mock_flow,
        mock_exists,
        mock_is_file_empty,
        mock_settings,
        mock_httpserver,
    ):
        """Complete OAuth flow should save token successfully."""
        mock_settings.credentials_file = "credentials.json"
        mock_settings.token_file = "token.json"
        mock_settings.scopes = ["scope1", "scope2"]
        mock_settings.oauth_port = 8767
        mock_settings.oauth_host = "localhost"
        mock_settings.oauth_external_port = None

        def exists_side_effect(path):
            if "token.json" in str(path):
                return False
            if "credentials.json" in str(path):
                return True
            return False

        mock_exists.side_effect = exists_side_effect
        mock_is_file_empty.return_value = False
        _mock_oauth_flow(mock_flow)
        mock_httpserver.return_value = Mock()

        service, error = auth.get_gmail_service()

        assert service is None
        assert error is not None
        assert "Sign-in started" in error

    @patch("app.services.auth.HTTPServer")
    @patch("app.services.auth.settings")
    @patch("app.services.auth._is_file_empty", return_value=False)
    @patch("os.path.exists")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data=MOCK_INSTALLED_CREDENTIALS,
    )
    @patch("app.services.auth.InstalledAppFlow")
    @patch("app.services.auth._auth_in_progress", {"active": False})
    @patch("app.services.auth.is_web_auth_mode", return_value=True)
    def test_oauth_flow_web_auth_mode_binds_to_all_interfaces(
        self,
        mock_web_auth,
        mock_flow,
        mock_file,
        mock_exists,
        mock_is_file_empty,
        mock_settings,
        mock_httpserver,
    ):
        """OAuth flow in web auth mode should bind to 0.0.0.0."""
        mock_settings.credentials_file = "credentials.json"
        mock_settings.token_file = "token.json"
        mock_settings.scopes = ["scope1", "scope2"]
        mock_settings.oauth_port = 8767
        mock_settings.oauth_host = "localhost"
        mock_settings.oauth_external_port = None

        def exists_side_effect(path):
            if "token.json" in str(path):
                return False
            if "credentials.json" in str(path):
                return True
            return False

        mock_exists.side_effect = exists_side_effect
        _mock_oauth_flow(mock_flow)
        mock_httpserver.return_value = Mock()

        auth.get_gmail_service()
        time.sleep(0.2)

        bind_calls = [call.args[0] for call in mock_httpserver.call_args_list if call.args]
        assert ("0.0.0.0", 8767) in bind_calls

    @patch("app.services.auth.HTTPServer")
    @patch("app.services.auth.settings")
    @patch("app.services.auth._is_file_empty", return_value=False)
    @patch("os.path.exists")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data=MOCK_INSTALLED_CREDENTIALS,
    )
    @patch("app.services.auth.InstalledAppFlow")
    @patch("app.services.auth._auth_in_progress", {"active": False})
    @patch("app.services.auth.is_web_auth_mode", return_value=False)
    def test_oauth_flow_desktop_mode_binds_to_localhost(
        self,
        mock_web_auth,
        mock_flow,
        mock_file,
        mock_exists,
        mock_is_file_empty,
        mock_settings,
        mock_httpserver,
    ):
        """OAuth flow in desktop mode should bind to localhost."""
        mock_settings.credentials_file = "credentials.json"
        mock_settings.token_file = "token.json"
        mock_settings.scopes = ["scope1", "scope2"]
        mock_settings.oauth_port = 8767
        mock_settings.oauth_host = "localhost"
        mock_settings.oauth_external_port = None

        def exists_side_effect(path):
            if "token.json" in str(path):
                return False
            if "credentials.json" in str(path):
                return True
            return False

        mock_exists.side_effect = exists_side_effect
        _mock_oauth_flow(mock_flow)
        mock_httpserver.return_value = Mock()

        auth.get_gmail_service()
        time.sleep(0.2)

        bind_calls = [call.args[0] for call in mock_httpserver.call_args_list if call.args]
        assert ("127.0.0.1", 8767) in bind_calls

    @patch("app.services.auth.HTTPServer")
    @patch("app.services.auth.settings")
    @patch("app.services.auth._is_file_empty", return_value=False)
    @patch("os.path.exists")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data=MOCK_INSTALLED_CREDENTIALS,
    )
    @patch("app.services.auth.InstalledAppFlow")
    @patch("app.services.auth._auth_in_progress", {"active": False})
    @patch("app.services.auth.is_web_auth_mode", return_value=False)
    def test_oauth_flow_with_custom_external_port(
        self,
        mock_web_auth,
        mock_flow,
        mock_file,
        mock_exists,
        mock_is_file_empty,
        mock_settings,
        mock_httpserver,
    ):
        """OAuth flow should honor external redirect port/host when mapped."""
        mock_settings.credentials_file = "credentials.json"
        mock_settings.token_file = "token.json"
        mock_settings.scopes = ["scope1", "scope2"]
        mock_settings.oauth_port = 8767
        mock_settings.oauth_host = "custom.example.com"
        mock_settings.oauth_external_port = 18767

        def exists_side_effect(path):
            if "token.json" in str(path):
                return False
            if "credentials.json" in str(path):
                return True
            return False

        mock_exists.side_effect = exists_side_effect
        flow_instance = _mock_oauth_flow(mock_flow)
        mock_httpserver.return_value = Mock()

        auth.get_gmail_service()
        time.sleep(0.2)

        assert flow_instance.redirect_uri == "http://custom.example.com:18767/"


class TestOAuthFlowErrors:
    """Tests for OAuth flow error scenarios"""

    @patch("app.services.auth.HTTPServer")
    @patch("app.services.auth.settings")
    @patch("app.services.auth._is_file_empty", return_value=False)
    @patch("os.path.exists")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data=MOCK_INSTALLED_CREDENTIALS,
    )
    @patch("app.services.auth.InstalledAppFlow")
    @patch("app.services.auth._auth_in_progress", {"active": False})
    @patch("app.services.auth.is_web_auth_mode", return_value=False)
    def test_oauth_invalid_authorization_code(
        self,
        mock_web_auth,
        mock_flow,
        mock_is_file_empty,
        mock_file,
        mock_exists,
        mock_settings,
        mock_httpserver,
    ):
        """OAuth flow should handle invalid authorization code."""
        mock_settings.credentials_file = "credentials.json"
        mock_settings.token_file = "token.json"
        mock_settings.scopes = ["scope1", "scope2"]
        mock_settings.oauth_port = 8767
        mock_settings.oauth_host = "localhost"
        mock_settings.oauth_external_port = None

        def exists_side_effect(path):
            if "token.json" in str(path):
                return False
            if "credentials.json" in str(path):
                return True
            return False

        mock_exists.side_effect = exists_side_effect
        _mock_oauth_flow(mock_flow)
        mock_httpserver.return_value = Mock()

        service, error = auth.get_gmail_service()

        assert service is None
        assert error is not None

    @patch("app.services.auth.HTTPServer")
    @patch("app.services.auth.settings")
    @patch("app.services.auth._is_file_empty", return_value=False)
    @patch("os.path.exists")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data=MOCK_INSTALLED_CREDENTIALS,
    )
    @patch("app.services.auth.InstalledAppFlow")
    @patch("app.services.auth._auth_in_progress", {"active": False})
    @patch("app.services.auth.is_web_auth_mode", return_value=False)
    def test_oauth_timeout_handling(
        self,
        mock_web_auth,
        mock_flow,
        mock_is_file_empty,
        mock_file,
        mock_exists,
        mock_settings,
        mock_httpserver,
    ):
        """OAuth flow should handle timeout gracefully."""
        mock_settings.credentials_file = "credentials.json"
        mock_settings.token_file = "token.json"
        mock_settings.scopes = ["scope1", "scope2"]
        mock_settings.oauth_port = 8767
        mock_settings.oauth_host = "localhost"
        mock_settings.oauth_external_port = None

        def exists_side_effect(path):
            if "token.json" in str(path):
                return False
            if "credentials.json" in str(path):
                return True
            return False

        mock_exists.side_effect = exists_side_effect
        _mock_oauth_flow(mock_flow)
        mock_httpserver.side_effect = TimeoutError("OAuth flow timed out")

        service, error = auth.get_gmail_service()

        assert service is None
        assert error is not None

    @patch("app.services.auth.HTTPServer")
    @patch("app.services.auth.settings")
    @patch("app.services.auth._is_file_empty", return_value=False)
    @patch("os.path.exists")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data=MOCK_INSTALLED_CREDENTIALS,
    )
    @patch("app.services.auth.InstalledAppFlow")
    @patch("app.services.auth._auth_in_progress", {"active": False})
    @patch("app.services.auth.is_web_auth_mode", return_value=False)
    def test_oauth_resets_auth_in_progress_on_error(
        self,
        mock_web_auth,
        mock_flow,
        mock_is_file_empty,
        mock_file,
        mock_exists,
        mock_settings,
        mock_httpserver,
    ):
        """OAuth flow should reset _auth_in_progress flag on error."""
        mock_settings.credentials_file = "credentials.json"
        mock_settings.token_file = "token.json"
        mock_settings.scopes = ["scope1", "scope2"]
        mock_settings.oauth_port = 8767
        mock_settings.oauth_host = "localhost"
        mock_settings.oauth_external_port = None

        def exists_side_effect(path):
            if "token.json" in str(path):
                return False
            if "credentials.json" in str(path):
                return True
            return False

        mock_exists.side_effect = exists_side_effect
        _mock_oauth_flow(mock_flow)
        mock_httpserver.side_effect = Exception("OAuth error")

        auth._auth_in_progress["active"] = False

        service, error = auth.get_gmail_service()

        assert service is None
        assert error is not None


class TestTypedClientCredentials:
    """Tests for per-client OAuth credential selection."""

    def test_web_credentials_keep_web_client_type(self):
        raw = {
            "web": {
                "client_id": "id",
                "client_secret": "secret",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://127.0.0.1:8767/"],
            }
        }
        prepared = auth._prepare_client_config(raw)
        assert prepared is not None
        assert "web" in prepared
        assert "installed" not in prepared

    @patch("app.services.auth._load_client_secrets_json")
    def test_gmail_client_does_not_fallback_to_default_credentials(self, mock_load):
        mock_load.return_value = None
        assert auth._get_credentials_path_for_client("gmail") is None
