"""Tests for coordinator missing-date handling."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eyeonsaur.coordinator import SaurCoordinator
from custom_components.eyeonsaur.helpers.const import (
    DOMAIN,
    ENTRY_CLIENTID,
    ENTRY_COMPTEURID,
    ENTRY_LOGIN,
    ENTRY_PASS,
    ENTRY_TOKEN,
)
from custom_components.eyeonsaur.models import (
    MissingDate,
    MissingDates,
    TheoreticalConsumptionDatas,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture(name="mock_config_entry")
def mock_config_entry_fixture() -> MockConfigEntry:
    """Return a complete coordinator config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            ENTRY_LOGIN: "test@example.com",
            ENTRY_PASS: "password",
            ENTRY_COMPTEURID: "section-123",
            ENTRY_TOKEN: "token",
            ENTRY_CLIENTID: "client-123",
        },
    )


async def test_async_handle_missing_dates_schedules_month(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A reduced missing date schedules retrieval of its month."""
    client = MagicMock()
    client.close_session = AsyncMock()
    with patch(
        "custom_components.eyeonsaur.coordinator.SaurClient",
        return_value=client,
    ):
        coordinator = SaurCoordinator(
            hass, mock_config_entry, AsyncMock(), AsyncMock()
        )
    compteur = MagicMock()
    compteur.sectionId = "section-123"
    missing = MissingDates([MissingDate(2024, 2, 10)])

    with (
        patch(
            "custom_components.eyeonsaur.coordinator.find_missing_dates",
            return_value=missing,
        ),
        patch(
            "custom_components.eyeonsaur.coordinator."
            "sync_reduce_missing_dates",
            return_value=missing,
        ),
        patch(
            "custom_components.eyeonsaur.coordinator.asyncio.sleep",
            new_callable=AsyncMock,
        ),
        patch.object(coordinator, "_sync_fetch_monthly_data") as fetch_month,
    ):
        await coordinator._async_handle_missing_dates(
            TheoreticalConsumptionDatas([]), compteur
        )
        await hass.async_block_till_done()

    fetch_month.assert_called_once_with(2024, 2, compteur)
