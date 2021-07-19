"""Platform for Kostal Plenticore sensors."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any, Callable

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ICON, ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_ENABLED_DEFAULT,
    DOMAIN,
    SENSOR_PROCESS_DATA,
    SENSOR_SETTINGS_DATA,
)
from .helper import (
    PlenticoreDataFormatter,
    ProcessDataUpdateCoordinator,
    SettingDataUpdateCoordinator,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Add kostal plenticore Sensors."""
    plenticore = hass.data[DOMAIN][entry.entry_id]

    entities = []

    available_process_data = await plenticore.client.get_process_data()
    process_data_update_coordinator = ProcessDataUpdateCoordinator(
        hass,
        _LOGGER,
        "Process Data",
        timedelta(seconds=10),
        plenticore,
    )
    for module_id, data_id, name, sensor_data, fmt in SENSOR_PROCESS_DATA:
        if (
            module_id not in available_process_data
            or data_id not in available_process_data[module_id]
        ):
            _LOGGER.debug(
                "Skipping non existing process data %s/%s", module_id, data_id
            )
            continue

        entities.append(
            PlenticoreDataSensor(
                process_data_update_coordinator,
                entry.entry_id,
                entry.title,
                module_id,
                data_id,
                name,
                sensor_data,
                PlenticoreDataFormatter.get_method(fmt),
                plenticore.device_info,
            )
        )

    available_settings_data = await plenticore.client.get_settings()
    settings_data_update_coordinator = SettingDataUpdateCoordinator(
        hass,
        _LOGGER,
        "Settings Data",
        timedelta(seconds=300),
        plenticore,
    )
    for module_id, data_id, name, sensor_data, fmt in SENSOR_SETTINGS_DATA:
        if module_id not in available_settings_data or data_id not in (
            setting.id for setting in available_settings_data[module_id]
        ):
            _LOGGER.debug(
                "Skipping non existing setting data %s/%s", module_id, data_id
            )
            continue

        entities.append(
            PlenticoreDataSensor(
                settings_data_update_coordinator,
                entry.entry_id,
                entry.title,
                module_id,
                data_id,
                name,
                sensor_data,
                PlenticoreDataFormatter.get_method(fmt),
                plenticore.device_info,
            )
        )

    async_add_entities(entities)


class PlenticoreDataSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Plenticore data Sensor."""

    def __init__(
        self,
        coordinator,
        entry_id: str,
        platform_name: str,
        module_id: str,
        data_id: str,
        sensor_name: str,
        sensor_data: dict[str, Any],
        formatter: Callable[[str], Any],
        device_info: DeviceInfo,
    ):
        """Create a new Sensor Entity for Plenticore process data."""
        super().__init__(coordinator)
        self.module_id = module_id
        self.data_id = data_id
        self._attr_name = f"{platform_name} {sensor_name}"
        self._attr_icon = sensor_data.get(ATTR_ICON)
        self._attr_unique_id = f"{entry_id}_{module_id}_{data_id}"
        self._attr_unit_of_measurement = sensor_data.get(ATTR_UNIT_OF_MEASUREMENT)
        self._formatter = formatter
        self._attr_device_class = sensor_data.get(ATTR_DEVICE_CLASS)
        self._attr_device_info = device_info
        self._attr_entity_registry_enabled_default = sensor_data.get(
            ATTR_ENABLED_DEFAULT, False
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available
            and self.coordinator.data is not None
            and self.module_id in self.coordinator.data
            and self.data_id in self.coordinator.data[self.module_id]
        )

    async def async_added_to_hass(self) -> None:
        """Register this entity on the Update Coordinator."""
        await super().async_added_to_hass()
        self.coordinator.start_fetch_data(self.module_id, self.data_id)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister this entity from the Update Coordinator."""
        self.coordinator.stop_fetch_data(self.module_id, self.data_id)
        await super().async_will_remove_from_hass()

    @property
    def state(self) -> Any | None:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            # None is translated to STATE_UNKNOWN
            return None

        raw_value = self.coordinator.data[self.module_id][self.data_id]

        return self._formatter(raw_value) if self._formatter else raw_value
