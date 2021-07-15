"""Support for the PRT Heatmiser themostats using the V3 protocol."""
from __future__ import annotations

import logging

from heatmiserV3 import connection, heatmiser
import voluptuous as vol

from homeassistant.components.climate import (
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    PLATFORM_SCHEMA,
    ClimateEntity,
)
from homeassistant.components.climate.const import SUPPORT_TARGET_TEMPERATURE
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_HOST,
    CONF_ID,
    CONF_NAME,
    CONF_PORT,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

CONF_THERMOSTATS = "tstats"

TSTATS_SCHEMA = vol.Schema(
    vol.All(
        cv.ensure_list,
        [{vol.Required(CONF_ID): cv.positive_int, vol.Required(CONF_NAME): cv.string}],
    )
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT): cv.string,
        vol.Optional(CONF_THERMOSTATS, default=[]): TSTATS_SCHEMA,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the heatmiser thermostat."""

    heatmiser_v3_thermostat = heatmiser.HeatmiserThermostat

    host = config[CONF_HOST]
    port = config[CONF_PORT]

    thermostats = config[CONF_THERMOSTATS]

    uh1_hub = connection.HeatmiserUH1(host, port)

    add_entities(
        [
            HeatmiserV3Thermostat(heatmiser_v3_thermostat, thermostat, uh1_hub)
            for thermostat in thermostats
        ],
        True,
    )


class HeatmiserV3Thermostat(ClimateEntity):
    """Representation of a HeatmiserV3 thermostat."""

    _attr_hvac_modes = [HVAC_MODE_HEAT, HVAC_MODE_OFF]
    _attr_supported_features = SUPPORT_TARGET_TEMPERATURE

    def __init__(self, therm, device, uh1):
        """Initialize the thermostat."""
        self.therm = therm(device[CONF_ID], "prt", uh1)
        self.uh1 = uh1
        self._attr_name = device[CONF_NAME]
        self.dcb = None
        self._attr_hvac_mode = HVAC_MODE_HEAT

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        self._attr_target_temperature = int(temperature)
        self.therm.set_target_temp(self.target_temperature)

    def update(self):
        """Get the latest data."""
        self.uh1.reopen()
        if not self.uh1.status:
            _LOGGER.error("Failed to update device %s", self.name)
            return
        self.dcb = self.therm.read_dcb()
        self._attr_temperature_unit = (
            TEMP_CELSIUS
            if (self.therm.get_temperature_format() == "C")
            else TEMP_FAHRENHEIT
        )
        self._attr_current_temperature = int(self.therm.get_floor_temp())
        self._attr_target_temperature = int(self.therm.get_target_temp())
        self._attr_hvac_mode = (
            HVAC_MODE_OFF
            if (int(self.therm.get_current_state()) == 0)
            else HVAC_MODE_HEAT
        )
