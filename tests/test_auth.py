"""Authentication unit tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.eyeonsaur.config_flow import check_credentials


@pytest.mark.asyncio
async def test_check_credentials_authenticates_client() -> None:
    """Credential validation delegates to the SAUR client."""
    client = MagicMock()
    client._authenticate = AsyncMock()

    await check_credentials(client)

    client._authenticate.assert_awaited_once()
