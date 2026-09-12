"""Tests for EyeOnSaur sensor entities."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
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
)
from custom_components.eyeonsaur.sensor import (
    EyeOnSaurSensor,
    async_setup_entry,
)

pytestmark = pytest.mark.asyncio


def make_compteur() -> Compteur:
    """Build a meter for sensor tests."""
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
) -> SaurCoordinator:
    """Build a coordinator with mocked persistence services."""
    with patch(
        "custom_components.eyeonsaur.coordinator.SaurClient",
        return_value=MagicMock(close_session=AsyncMock()),
    ):
        return SaurCoordinator(hass, entry, AsyncMock(), AsyncMock())


async def test_setup_adds_display_only_estimated_index_sensor(
    hass: HomeAssistant,
) -> None:
    """Expose the latest cumulative index without automatic statistics."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            ENTRY_LOGIN: "test@example.com",
            ENTRY_PASS: "password",
            ENTRY_COMPTEURID: "section-123",
            ENTRY_TOKEN: "token",
            ENTRY_CLIENTID: "client-123",
        },
    )
    compteur = make_compteur()
    coordinator = make_coordinator(hass, entry)
    coordinator.async_set_updated_data(
        SaurData(
            saurClientId=ClientId("client-123"),
            compteurs=Compteurs([compteur]),
            contracts=Contracts([]),
        )
    )
    coordinator.latest_water_indexes[compteur.sectionId] = 211.29
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator
    }
    entities: list[EyeOnSaurSensor] = []

    def add_entities(
        new_entities: list[EyeOnSaurSensor], update_before_add: bool
    ) -> None:
        assert update_before_add is True
        entities.extend(new_entities)

    await async_setup_entry(hass, entry, add_entities)

    index_sensor = next(
        entity
        for entity in entities
        if entity._sensor_type == "estimated_meter_index"
    )
    assert len(entities) == 6
    assert index_sensor.name == "Index estimé du compteur"
    assert index_sensor.native_value == 211.29
    assert index_sensor.native_unit_of_measurement == UnitOfVolume.CUBIC_METERS
    assert index_sensor.device_class == SensorDeviceClass.WATER
    assert index_sensor.state_class is None
    assert index_sensor.unique_id == "SECTION-123_estimated_meter_index"

    coordinator.latest_water_indexes[compteur.sectionId] = 212.0
    assert index_sensor.native_value == 212.0


async def test_estimated_index_sensor_is_unavailable_without_history(
    hass: HomeAssistant,
) -> None:
    """Do not present an unknown index as a valid zero reading."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            ENTRY_LOGIN: "test@example.com",
            ENTRY_PASS: "password",
            ENTRY_COMPTEURID: "section-123",
            ENTRY_TOKEN: "token",
            ENTRY_CLIENTID: "client-123",
        },
    )
    compteur = make_compteur()
    coordinator = make_coordinator(hass, entry)
    coordinator.async_set_updated_data(
        SaurData(
            saurClientId=ClientId("client-123"),
            compteurs=Compteurs([compteur]),
            contracts=Contracts([]),
        )
    )
    sensor = EyeOnSaurSensor(
        coordinator,
        compteur,
        "estimated_meter_index",
        DeviceInfo(identifiers={(DOMAIN, compteur.serial_number)}),
    )

    assert sensor.native_value is None
    assert sensor.available is False
