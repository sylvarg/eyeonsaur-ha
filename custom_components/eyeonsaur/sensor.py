"""Module de gestion du capteur pour l'intégration EyeOnSaur."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import (
    DeviceInfo,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .coordinator import SaurCoordinator
from .device import Compteur
from .helpers.const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure la plateforme de capteur via un config flow."""
    _LOGGER.debug("Configuration de la plateforme de capteur via config flow.")

    coordinator: SaurCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    entities: list[EyeOnSaurSensor] = []
    for compteur in coordinator.data.compteurs:
        if compteur.isContractTerminated:
            continue  # Ignore les compteurs avec contrat terminé

        device_info_compteur = DeviceInfo(
            identifiers={(DOMAIN, compteur.serial_number)},
            name=f"Compteur {compteur.serial_number}",
            manufacturer=compteur.manufacturer,
            model=compteur.model,
            via_device=(DOMAIN, compteur.clientReference),
            serial_number=compteur.serial_number,
            sw_version=compteur.sectionId,
        )

        # device_info_contrat = DeviceInfo(
        #         identifiers={(DOMAIN, compteur.clientReference)},
        #         name=f"Contrat {compteur.clientReference}",
        #         manufacturer="SAUR",
        #         model=f"Contrat {compteur.clientReference}",
        # )

        # Création des capteurs
        sensor_types = [
            "serial_number",
            "installation_date",
            "last_reading_value",
            "last_reading_date",
            "contract_terminated",
            "estimated_meter_index",
        ]

        entities.extend(
            EyeOnSaurSensor(coordinator, compteur, sensor, device_info_compteur)
            for sensor in sensor_types
        )
        # entities.append(EyeOnSaurSensor(coordinator,
        # compteur, "water_consumption", device_info))
    async_add_entities(entities, update_before_add=True)


class EyeOnSaurSensor(CoordinatorEntity[SaurCoordinator], SensorEntity):
    """Représentation d'un capteur EyeOnSaur."""

    _attr_has_entity_name = True
    _attr_translation_key = "water_consumption"
    # _attr_native_unit_of_measurement = None
    # _attr_state_class = None

    def __init__(
        self,
        coordinator: SaurCoordinator,
        compteur: Compteur,
        sensor_type: str,
        device_info: DeviceInfo,
    ) -> None:
        """Initialisation du capteur."""
        super().__init__(coordinator)
        self._coordinator: SaurCoordinator = coordinator
        self._compteur: Compteur = compteur
        self._sensor_type: str = sensor_type
        self._attr_unique_id = f"{compteur.sectionId}_{sensor_type}"
        self._attr_device_info = device_info
        self._attr_name = f"{self.get_sensor_name()}"
        self._attr_should_poll = False

        # Définition du device_class et unité de mesure si nécessaire
        if self._sensor_type in {
            "last_reading_value",
            "estimated_meter_index",
        }:
            self._attr_device_class = SensorDeviceClass.WATER
            self._attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
        elif self._sensor_type in ["installation_date", "last_reading_date"]:
            self._attr_device_class = SensorDeviceClass.DATE

    def get_sensor_name(self) -> str:
        """Retourne le nom du capteur."""
        return {
            "serial_number": "Numéro de série",
            "installation_date": "Date d'installation",
            "last_reading_value": "Dernier relevé (technicien)",
            "last_reading_date": "Date du dernier relevé (technicien)",
            "contract_terminated": "Contrat terminé",
            "estimated_meter_index": "Index estimé du compteur",
        }.get(self._sensor_type, self._sensor_type)

    @property
    def available(self) -> bool:  # pyright: ignore
        """Return if entity is available."""
        if self._sensor_type == "estimated_meter_index":
            return (
                super().available
                and self._compteur.sectionId
                in self._coordinator.latest_water_indexes
            )
        return super().available

    @property
    def native_value(self) -> Any:
        """
        Retourne la valeur du capteur."""

        retour: Any = None  # Initialisation de la variable retour

        if self._sensor_type == "serial_number":
            retour = self._compteur.serial_number
        elif self._sensor_type == "installation_date":
            installation_date = datetime.fromisoformat(
                self._compteur.date_installation
            )
            retour = dt_util.as_utc(installation_date)
        elif self._sensor_type == "last_reading_date":
            last_reading_date = dt_util.parse_datetime(
                self._compteur.releve_physique.date
            )
            if (
                last_reading_date is not None
                and last_reading_date.tzinfo is None
            ):
                last_reading_date = dt_util.as_utc(last_reading_date)
            retour = last_reading_date
        elif self._sensor_type == "contract_terminated":
            retour = self._compteur.isContractTerminated
        elif self._sensor_type == "last_reading_value":
            retour = self._compteur.releve_physique.valeur
        elif self._sensor_type == "estimated_meter_index":
            retour = self._coordinator.latest_water_indexes.get(
                self._compteur.sectionId
            )

        return retour  # Retourne la valeur à la fin

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Retourne les attributs supplémentaires."""
        if self._sensor_type == "last_reading_value":
            return {"last_updated": self._compteur.releve_physique.date}
        return None
