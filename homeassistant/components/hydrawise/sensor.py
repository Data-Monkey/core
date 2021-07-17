"""Support for Hydrawise sprinkler sensors."""
import logging

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import CONF_MONITORED_CONDITIONS
import homeassistant.helpers.config_validation as cv
from homeassistant.util import dt

from . import DATA_HYDRAWISE, DEVICE_MAP, DEVICE_MAP_INDEX, SENSORS, HydrawiseEntity

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_MONITORED_CONDITIONS, default=SENSORS): vol.All(
            cv.ensure_list, [vol.In(SENSORS)]
        )
    }
)

TWO_YEAR_SECONDS = 60 * 60 * 24 * 365 * 2
WATERING_TIME_ICON = "mdi:water-pump"


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up a sensor for a Hydrawise device."""
    hydrawise = hass.data[DATA_HYDRAWISE].data

    sensors = []
    for sensor_type in config.get(CONF_MONITORED_CONDITIONS):
        for zone in hydrawise.relays:
            sensors.append(HydrawiseSensor(zone, sensor_type))

    add_entities(sensors, True)


class HydrawiseSensor(HydrawiseEntity, SensorEntity):
    """A sensor implementation for Hydrawise device."""

    def update(self):
        """Get the latest data and updates the states."""
        mydata = self.hass.data[DATA_HYDRAWISE].data
        _LOGGER.debug("Updating Hydrawise sensor: %s", self.name)
        relay_data = mydata.relays[self.data["relay"] - 1]
        if self._sensor_type == "watering_time":
            if relay_data["timestr"] == "Now":
                self._attr_state = int(relay_data["run"] / 60)
            else:
                self._attr_state = 0
        else:  # _sensor_type == 'next_cycle'
            next_cycle = min(relay_data["time"], TWO_YEAR_SECONDS)
            _LOGGER.debug("New cycle time: %s", next_cycle)
            self._attr_state = dt.utc_from_timestamp(
                dt.as_timestamp(dt.now()) + next_cycle
            ).isoformat()
        self._attr_unit_of_measurement = DEVICE_MAP[self._sensor_type][
            DEVICE_MAP_INDEX.index("UNIT_OF_MEASURE_INDEX")
        ]
