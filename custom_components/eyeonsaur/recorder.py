"""Import EyeOnSaur historical data as external statistics."""

import logging
from datetime import datetime

from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
)
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

from .helpers.const import DOMAIN
from .models import SectionId, TheoreticalConsumptionDatas

_LOGGER = logging.getLogger(__name__)

STATISTIC_UNIT_CLASS = "volume"


def water_statistic_id(section_id: SectionId) -> str:
    """Build the stable external statistic ID for a SAUR section."""
    object_id = slugify(f"{section_id}_water_consumption")
    if not object_id:
        raise ValueError("A section ID is required to build a statistic ID")
    return f"{DOMAIN}:{object_id}"


class SaurRecorder:
    """Import cumulative water-meter readings into the HA recorder."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the recorder service."""
        self.hass = hass

    async def async_inject_historical_data(
        self,
        statistic_id: str,
        statistic_name: str,
        consumptions: TheoreticalConsumptionDatas,
    ) -> None:
        """Import cumulative readings as an external HA statistic."""
        metadata: StatisticMetaData = {
            "has_sum": True,
            "mean_type": StatisticMeanType.NONE,
            "name": statistic_name,
            "source": DOMAIN,
            "statistic_id": statistic_id,
            "unit_class": STATISTIC_UNIT_CLASS,
            "unit_of_measurement": UnitOfVolume.CUBIC_METERS,
        }

        statistics: list[StatisticData] = []
        today = dt_util.now().date()
        for consumption in sorted(consumptions, key=lambda item: item.date):
            consumption_date = datetime.fromisoformat(consumption.date).date()
            if consumption_date > today:
                continue

            # SAUR values are daily local readings. Recorder accepts timezone-
            # aware timestamps at the top of an hour and normalizes them to
            # UTC.
            start = dt_util.start_of_local_day(consumption_date)
            statistics.append(
                StatisticData(
                    start=start,
                    state=consumption.indexValue,
                    sum=consumption.indexValue,
                )
            )

        if not statistics:
            return

        async_add_external_statistics(self.hass, metadata, statistics)
        _LOGGER.debug(
            "Imported %s historical points for %s",
            len(statistics),
            statistic_id,
        )
