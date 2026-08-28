"""Tests for the EyeOnSaur coordinator."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eyeonsaur.coordinator import SaurCoordinator
from custom_components.eyeonsaur.device import Compteur, Compteurs
from custom_components.eyeonsaur.helpers.const import (
    DOMAIN,
    ENTRY_CLIENTID,
    ENTRY_COMPTEURID,
    ENTRY_LOGIN,
    ENTRY_PASS,
    ENTRY_TOKEN,
)
from custom_components.eyeonsaur.models import (
    ClientId,
    Contracts,
    ContratId,
    RelevePhysique,
    SaurData,
    SectionId,
    StrDate,
    TheoreticalConsumptionData,
    TheoreticalConsumptionDatas,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture(name="mock_config_entry")
def mock_config_entry_fixture() -> MockConfigEntry:
    """Return a complete config entry accepted by the current coordinator."""
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


def make_compteur() -> Compteur:
    """Build a meter with an installation date before its physical reading."""
    return Compteur(
        sectionId=SectionId("SECTION-123"),
        clientReference="reference-123",
        clientId=ClientId("client-123"),
        contractName="Contrat test",
        contractId=ContratId("contract-123"),
        isContractTerminated=False,
        date_installation=StrDate("2024-01-15T00:00:00"),
        pairingTechnologyCode="AMR",
        releve_physique=RelevePhysique(
            date=StrDate("2024-03-20T00:00:00"), valeur=100.0
        ),
        manufacturer="SAUR",
        model="Test",
        serial_number="SERIAL-123",
    )


def make_coordinator(
    hass: HomeAssistant, entry: MockConfigEntry
) -> tuple[SaurCoordinator, AsyncMock, AsyncMock]:
    """Build a coordinator with mocked persistence services."""
    db_helper = AsyncMock()
    recorder = AsyncMock()
    client = MagicMock()
    client.close_session = AsyncMock()
    with patch(
        "custom_components.eyeonsaur.coordinator.SaurClient",
        return_value=client,
    ):
        coordinator = SaurCoordinator(hass, entry, db_helper, recorder)
    return coordinator, db_helper, recorder


async def test_coordinator_init(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Coordinator keeps the injected persistence services."""
    coordinator, db_helper, recorder = make_coordinator(hass, mock_config_entry)
    assert coordinator.db_helper is db_helper
    assert coordinator.recorder is recorder
    assert coordinator.data is None


async def test_initial_backfill_schedules_every_month_from_installation(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """An empty installation month cannot prevent later-month backfill."""
    mock_config_entry.add_to_hass(hass)
    coordinator, db_helper, _ = make_coordinator(hass, mock_config_entry)
    compteur = make_compteur()
    saur_data = SaurData(
        saurClientId=ClientId("client-123"),
        compteurs=Compteurs([compteur]),
        contracts=Contracts([]),
    )
    coordinator.client.get_contracts = AsyncMock(
        return_value={
            "clients": [
                {"clientId": "client-123", "contractName": "Contrat test"}
            ]
        }
    )
    coordinator.client.access_token = "token"
    coordinator.update_compteurs_with_delivery_points = AsyncMock(
        return_value=saur_data
    )

    with (
        patch(
            "custom_components.eyeonsaur.coordinator."
            "extract_compteurs_from_area",
            return_value=Compteurs([compteur]),
        ),
        patch(
            "custom_components.eyeonsaur.coordinator.hass_now",
            return_value=datetime(2024, 4, 10, tzinfo=UTC),
        ),
        patch.object(
            coordinator, "_async_fetch_monthly_data", new_callable=AsyncMock
        ) as fetch_month,
        patch(
            "homeassistant.helpers.update_coordinator.DataUpdateCoordinator."
            "async_config_entry_first_refresh",
            new_callable=AsyncMock,
        ),
    ):
        await coordinator.async_config_entry_first_refresh()
        await hass.async_block_till_done()

    db_helper.async_init_db.assert_awaited_once()
    assert [
        (call.kwargs["year"], call.kwargs["month"])
        for call in fetch_month.await_args_list
    ] == [(2024, 1), (2024, 2), (2024, 3), (2024, 4)]
    assert all(
        call.kwargs["reconcile_history"] is False
        for call in fetch_month.await_args_list
    )


async def test_historical_injection_does_not_use_entity_registry(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Coordinator imports directly to the stable external statistic ID."""
    coordinator, _, recorder = make_coordinator(hass, mock_config_entry)
    compteur = make_compteur()
    consumptions = TheoreticalConsumptionDatas(
        [
            TheoreticalConsumptionData(
                date=StrDate("2024-01-02 00:00:00"), indexValue=101.5
            ),
            TheoreticalConsumptionData(
                date=StrDate("2024-01-01 00:00:00"), indexValue=100.0
            ),
        ]
    )

    await coordinator._async_inject_historical_data(consumptions, compteur)

    recorder.async_inject_historical_data.assert_awaited_once_with(
        "eyeonsaur:section_123_water_consumption",
        "Consommation d'eau SAUR SERIAL-123",
        consumptions,
    )
    assert coordinator.latest_water_indexes[compteur.sectionId] == 101.5


async def test_periodic_update_refreshes_index_after_weekly_and_anchor_data(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The display sensor and external statistic stay current after setup."""
    coordinator, _, _ = make_coordinator(hass, mock_config_entry)
    compteur = make_compteur()
    coordinator._cached_data = SaurData(
        saurClientId=ClientId("client-123"),
        compteurs=Compteurs([compteur]),
        contracts=Contracts([]),
    )
    coordinator._async_fetch_and_store_weekly_data = AsyncMock()
    coordinator._async_backgroundupdate_data = AsyncMock()
    coordinator._async_refresh_historical_data = AsyncMock(
        return_value=TheoreticalConsumptionDatas([])
    )
    coordinator._async_handle_missing_dates = AsyncMock()

    result = await coordinator._async_update_data()

    assert result is coordinator._cached_data
    coordinator._async_fetch_and_store_weekly_data.assert_awaited_once_with(
        compteur=compteur
    )
    coordinator._async_backgroundupdate_data.assert_awaited_once_with(compteur)
    coordinator._async_refresh_historical_data.assert_awaited_once_with(
        compteur
    )
    coordinator._async_handle_missing_dates.assert_awaited_once_with(
        TheoreticalConsumptionDatas([]), compteur
    )


async def test_initial_month_fetch_defers_history_reconciliation(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Bulk backfill stores each month without repeatedly importing history."""
    coordinator, _, _ = make_coordinator(hass, mock_config_entry)
    compteur = make_compteur()
    coordinator._async_apifetch_and_sqlstore_monthly_data = AsyncMock()
    coordinator._async_refresh_historical_data = AsyncMock()
    coordinator._async_handle_missing_dates = AsyncMock()

    await coordinator._async_fetch_monthly_data(
        2024,
        1,
        compteur,
        reconcile_history=False,
    )

    coordinator._async_apifetch_and_sqlstore_monthly_data.assert_awaited_once_with(
        2024, 1, compteur.sectionId
    )
    coordinator._async_refresh_historical_data.assert_not_awaited()
    coordinator._async_handle_missing_dates.assert_not_awaited()


async def test_estimated_index_ignores_future_consumptions(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A future API placeholder must not become the displayed index."""
    coordinator, _, recorder = make_coordinator(hass, mock_config_entry)
    compteur = make_compteur()
    consumptions = TheoreticalConsumptionDatas(
        [
            TheoreticalConsumptionData(
                date=StrDate("2026-08-28 00:00:00"), indexValue=211.29
            ),
            TheoreticalConsumptionData(
                date=StrDate("2026-08-29 00:00:00"), indexValue=999.0
            ),
        ]
    )

    with patch(
        "custom_components.eyeonsaur.coordinator.hass_now",
        return_value=datetime(2026, 8, 28, 12, tzinfo=UTC),
    ):
        await coordinator._async_inject_historical_data(consumptions, compteur)

    assert coordinator.latest_water_indexes[compteur.sectionId] == 211.29
    recorder.async_inject_historical_data.assert_awaited_once()
