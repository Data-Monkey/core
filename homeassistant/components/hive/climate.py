"""Support for the Hive climate devices."""
from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_OFF,
    HVAC_MODE_AUTO,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    PRESET_BOOST,
    PRESET_NONE,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS, TEMP_FAHRENHEIT
from homeassistant.helpers import config_validation as cv, entity_platform

from . import HiveEntity, refresh_system
from .const import (
    ATTR_TIME_PERIOD,
    DOMAIN,
    SERVICE_BOOST_HEATING_OFF,
    SERVICE_BOOST_HEATING_ON,
)

HIVE_TO_HASS_STATE = {
    "SCHEDULE": HVAC_MODE_AUTO,
    "MANUAL": HVAC_MODE_HEAT,
    "OFF": HVAC_MODE_OFF,
}

HASS_TO_HIVE_STATE = {
    HVAC_MODE_AUTO: "SCHEDULE",
    HVAC_MODE_HEAT: "MANUAL",
    HVAC_MODE_OFF: "OFF",
}

HIVE_TO_HASS_HVAC_ACTION = {
    "UNKNOWN": CURRENT_HVAC_OFF,
    False: CURRENT_HVAC_IDLE,
    True: CURRENT_HVAC_HEAT,
}

TEMP_UNIT = {"C": TEMP_CELSIUS, "F": TEMP_FAHRENHEIT}

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE
SUPPORT_HVAC = [HVAC_MODE_AUTO, HVAC_MODE_HEAT, HVAC_MODE_OFF]
SUPPORT_PRESET = [PRESET_NONE, PRESET_BOOST]
PARALLEL_UPDATES = 0
SCAN_INTERVAL = timedelta(seconds=15)
_LOGGER = logging.getLogger()


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Hive thermostat based on a config entry."""

    hive = hass.data[DOMAIN][entry.entry_id]
    devices = hive.session.deviceList.get("climate")
    entities = []
    if devices:
        for dev in devices:
            entities.append(HiveClimateEntity(hive, dev))
    async_add_entities(entities, True)

    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        "boost_heating",
        {
            vol.Required(ATTR_TIME_PERIOD): vol.All(
                cv.time_period,
                cv.positive_timedelta,
                lambda td: td.total_seconds() // 60,
            ),
            vol.Optional(ATTR_TEMPERATURE, default="25.0"): vol.Coerce(float),
        },
        "async_heating_boost",
    )

    platform.async_register_entity_service(
        SERVICE_BOOST_HEATING_ON,
        {
            vol.Required(ATTR_TIME_PERIOD): vol.All(
                cv.time_period,
                cv.positive_timedelta,
                lambda td: td.total_seconds() // 60,
            ),
            vol.Optional(ATTR_TEMPERATURE, default="25.0"): vol.Coerce(float),
        },
        "async_heating_boost_on",
    )

    platform.async_register_entity_service(
        SERVICE_BOOST_HEATING_OFF,
        {},
        "async_heating_boost_off",
    )


class HiveClimateEntity(HiveEntity, ClimateEntity):
    """Hive Climate Device."""

    _attr_hvac_modes = SUPPORT_HVAC
    _attr_preset_modes = SUPPORT_PRESET
    _attr_supported_features = SUPPORT_FLAGS

    def __init__(self, hive_session, hive_device):
        """Initialize the Climate device."""
        super().__init__(hive_session, hive_device)
        self.thermostat_node_id = hive_device["device_id"]
        self._attr_name = hive_device["haName"]
        self._attr_temperature_unit = TEMP_UNIT.get(hive_device["temperatureunit"])
        self._attr_min_temp = hive_device["min_temp"]
        self._attr_max_temp = hive_device["max_temp"]
        self._attr_device_info = {
            "identifiers": {(DOMAIN, hive_device["device_id"])},
            "name": hive_device["device_name"],
            "model": hive_device["deviceData"]["model"],
            "manufacturer": hive_device["deviceData"]["manufacturer"],
            "sw_version": hive_device["deviceData"]["version"],
            "via_device": (DOMAIN, hive_device["parentDevice"]),
        }

    @refresh_system
    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        new_mode = HASS_TO_HIVE_STATE[hvac_mode]
        await self.hive.heating.setMode(self.device, new_mode)

    @refresh_system
    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        new_temperature = kwargs.get(ATTR_TEMPERATURE)
        if new_temperature is not None:
            await self.hive.heating.setTargetTemperature(self.device, new_temperature)

    @refresh_system
    async def async_set_preset_mode(self, preset_mode):
        """Set new preset mode."""
        if preset_mode == PRESET_NONE and self.preset_mode == PRESET_BOOST:
            await self.hive.heating.setBoostOff(self.device)
        elif preset_mode == PRESET_BOOST:
            curtemp = round(self.current_temperature * 2) / 2
            temperature = curtemp + 0.5
            await self.hive.heating.setBoostOn(self.device, 30, temperature)

    async def async_heating_boost(self, time_period, temperature):
        """Handle boost heating service call."""
        _LOGGER.warning(
            "Hive Service heating_boost will be removed in 2021.7.0, please update to heating_boost_on"
        )
        await self.async_heating_boost_on(time_period, temperature)

    @refresh_system
    async def async_heating_boost_on(self, time_period, temperature):
        """Handle boost heating service call."""
        await self.hive.heating.setBoostOn(self.device, time_period, temperature)

    @refresh_system
    async def async_heating_boost_off(self):
        """Handle boost heating service call."""
        await self.hive.heating.setBoostOff(self.device)

    async def async_update(self):
        """Update all Node data from Hive."""
        await self.hive.session.updateData(self.device)
        self.device = await self.hive.heating.getClimate(self.device)
        self._attr_available = self.device["deviceData"]["online"]
        self._attr_hvac_mode = HIVE_TO_HASS_STATE[self.device["status"]["mode"]]
        self._attr_hvac_action = HIVE_TO_HASS_HVAC_ACTION[
            self.device["status"]["action"]
        ]
        self._attr_current_temperature = self.device["status"]["current_temperature"]
        self._attr_target_temperature = self.device["status"]["target_temperature"]
        self._attr_preset_mode = None
        if self.device["status"]["boost"] == "ON":
            self._attr_preset_mode = PRESET_BOOST
