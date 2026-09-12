"""Tests for the SAUR client factory."""

from unittest.mock import patch

from custom_components.eyeonsaur.config_flow import create_saur_client
from custom_components.eyeonsaur.helpers.const import DEV


def test_create_saur_client_uses_configured_mode() -> None:
    """The client factory passes credentials and the integration mode."""
    with patch(
        "custom_components.eyeonsaur.config_flow.SaurClient"
    ) as saur_client:
        client = create_saur_client(
            login="test_login", password="test_password"
        )

    assert client is saur_client.return_value
    saur_client.assert_called_once_with(
        login="test_login",
        password="test_password",
        dev_mode=DEV,
    )
