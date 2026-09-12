"""Tests for EyeOnSaur external recorder statistics."""

from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from homeassistant.components.recorder.models import StatisticMeanType
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.eyeonsaur.helpers.const import DOMAIN
from custom_components.eyeonsaur.models import (
    SectionId,
    StrDate,
    TheoreticalConsumptionData,
    TheoreticalConsumptionDatas,
)
from custom_components.eyeonsaur.recorder import (
    SaurRecorder,
    water_statistic_id,
)


def test_water_statistic_id_is_stable_and_external() -> None:
    """The statistic ID is independent from an HA entity ID."""
    assert (
        water_statistic_id(SectionId("ABC-123"))
        == "eyeonsaur:abc_123_water_consumption"
    )


@pytest.mark.asyncio
async def test_async_injects_external_statistics_metadata_and_local_dates(
    hass: HomeAssistant,
) -> None:
    """External metadata is current and daily timestamps use HA local time."""
    previous_time_zone = dt_util.get_default_time_zone()
    paris = ZoneInfo("Europe/Paris")
    dt_util.set_default_time_zone(paris)
    consumptions = TheoreticalConsumptionDatas(
        [
            TheoreticalConsumptionData(
                date=StrDate("2026-08-28 00:00:00"), indexValue=102.0
            ),
            TheoreticalConsumptionData(
                date=StrDate("2026-08-26 00:00:00"), indexValue=100.0
            ),
            TheoreticalConsumptionData(
                date=StrDate("2026-08-27 00:00:00"), indexValue=101.0
            ),
        ]
    )

    try:
        with (
            patch(
                "custom_components.eyeonsaur.recorder.dt_util.now",
                return_value=datetime(2026, 8, 27, 12, tzinfo=paris),
            ),
            patch(
                "custom_components.eyeonsaur.recorder."
                "async_add_external_statistics"
            ) as import_statistics,
        ):
            await SaurRecorder(hass).async_inject_historical_data(
                "eyeonsaur:abc_123_water_consumption",
                "Consommation d'eau SAUR ABC-123",
                consumptions,
            )
    finally:
        dt_util.set_default_time_zone(previous_time_zone)

    import_statistics.assert_called_once()
    _, metadata, statistics = import_statistics.call_args.args
    assert metadata == {
        "has_sum": True,
        "mean_type": StatisticMeanType.NONE,
        "name": "Consommation d'eau SAUR ABC-123",
        "source": DOMAIN,
        "statistic_id": "eyeonsaur:abc_123_water_consumption",
        "unit_class": "volume",
        "unit_of_measurement": UnitOfVolume.CUBIC_METERS,
    }
    assert statistics == [
        {
            "start": datetime(2026, 8, 26, tzinfo=paris),
            "state": 100.0,
            "sum": 100.0,
        },
        {
            "start": datetime(2026, 8, 27, tzinfo=paris),
            "state": 101.0,
            "sum": 101.0,
        },
    ]
    assert all("last_reset" not in statistic for statistic in statistics)
