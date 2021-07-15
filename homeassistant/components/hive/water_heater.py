"""Support for hive water heaters."""

from datetime import timedelta

import voluptuous as vol

from homeassistant.components.water_heater import (
    STATE_ECO,
    STATE_OFF,
    STATE_ON,
    SUPPORT_OPERATION_MODE,
    WaterHeaterEntity,
)
from homeassistant.const import TEMP_CELSIUS
from homeassistant.helpers import config_validation as cv, entity_platform

from . import HiveEntity, refresh_system
from .const import (
    ATTR_ONOFF,
    ATTR_TIME_PERIOD,
    DOMAIN,
    SERVICE_BOOST_HOT_WATER,
    WATER_HEATER_MODES,
)

SUPPORT_FLAGS_HEATER = SUPPORT_OPERATION_MODE
HOTWATER_NAME = "Hot Water"
PARALLEL_UPDATES = 0
SCAN_INTERVAL = timedelta(seconds=15)
HIVE_TO_HASS_STATE = {
    "SCHEDULE": STATE_ECO,
    "ON": STATE_ON,
    "OFF": STATE_OFF,
}

HASS_TO_HIVE_STATE = {
    STATE_ECO: "SCHEDULE",
    STATE_ON: "MANUAL",
    STATE_OFF: "OFF",
}

SUPPORT_WATER_HEATER = [STATE_ECO, STATE_ON, STATE_OFF]


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Hive thermostat based on a config entry."""

    hive = hass.data[DOMAIN][entry.entry_id]
    devices = hive.session.deviceList.get("water_heater")
    entities = []
    if devices:
        for dev in devices:
            entities.append(HiveWaterHeater(hive, dev))
    async_add_entities(entities, True)

    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        SERVICE_BOOST_HOT_WATER,
        {
            vol.Optional(ATTR_TIME_PERIOD, default="00:30:00"): vol.All(
                cv.time_period,
                cv.positive_timedelta,
                lambda td: td.total_seconds() // 60,
            ),
            vol.Required(ATTR_ONOFF): vol.In(WATER_HEATER_MODES),
        },
        "async_hot_water_boost",
    )


class HiveWaterHeater(HiveEntity, WaterHeaterEntity):
    """Hive Water Heater Device."""

    _attr_name = HOTWATER_NAME
    _attr_operation_list = SUPPORT_WATER_HEATER
    _attr_supported_features = SUPPORT_FLAGS_HEATER
    _attr_temperature_unit = TEMP_CELSIUS

    def __init__(self, hive, hive_device):
        """Initialize a Hive Water Heater Device."""
        super().__init__(hive, hive_device)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, hive_device["device_id"])},
            "name": hive_device["device_name"],
            "model": hive_device["deviceData"]["model"],
            "manufacturer": hive_device["deviceData"]["manufacturer"],
            "sw_version": hive_device["deviceData"]["version"],
            "via_device": (DOMAIN, hive_device["parentDevice"]),
        }

    @refresh_system
    async def async_turn_on(self, **kwargs):
        """Turn on hotwater."""
        await self.hive.hotwater.setMode(self.device, "MANUAL")

    @refresh_system
    async def async_turn_off(self, **kwargs):
        """Turn on hotwater."""
        await self.hive.hotwater.setMode(self.device, "OFF")

    @refresh_system
    async def async_set_operation_mode(self, operation_mode):
        """Set operation mode."""
        new_mode = HASS_TO_HIVE_STATE[operation_mode]
        await self.hive.hotwater.setMode(self.device, new_mode)

    @refresh_system
    async def async_hot_water_boost(self, time_period, on_off):
        """Handle the service call."""
        if on_off == "on":
            await self.hive.hotwater.setBoostOn(self.device, time_period)
        elif on_off == "off":
            await self.hive.hotwater.setBoostOff(self.device)

    async def async_update(self):
        """Update all Node data from Hive."""
        await self.hive.session.updateData(self.device)
        self.device = await self.hive.hotwater.getWaterHeater(self.device)
        self._attr_available = self.device["deviceData"]["online"]
        self._attr_current_operation = HIVE_TO_HASS_STATE[
            self.device["status"]["current_operation"]
        ]
