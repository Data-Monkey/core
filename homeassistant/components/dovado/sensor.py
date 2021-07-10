"""Support for sensors from the Dovado router."""
from datetime import timedelta
import re

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import CONF_SENSORS, DATA_GIGABYTES, PERCENTAGE
import homeassistant.helpers.config_validation as cv

from . import DOMAIN as DOVADO_DOMAIN

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)

SENSOR_UPLOAD = "upload"
SENSOR_DOWNLOAD = "download"
SENSOR_SIGNAL = "signal"
SENSOR_NETWORK = "network"
SENSOR_SMS_UNREAD = "sms"

SENSORS = {
    SENSOR_NETWORK: ("signal strength", "Network", None, "mdi:access-point-network"),
    SENSOR_SIGNAL: (
        "signal strength",
        "Signal Strength",
        PERCENTAGE,
        "mdi:signal",
    ),
    SENSOR_SMS_UNREAD: ("sms unread", "SMS unread", "", "mdi:message-text-outline"),
    SENSOR_UPLOAD: ("traffic modem tx", "Sent", DATA_GIGABYTES, "mdi:cloud-upload"),
    SENSOR_DOWNLOAD: (
        "traffic modem rx",
        "Received",
        DATA_GIGABYTES,
        "mdi:cloud-download",
    ),
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Required(CONF_SENSORS): vol.All(cv.ensure_list, [vol.In(SENSORS)])}
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Dovado sensor platform."""
    dovado = hass.data[DOVADO_DOMAIN]

    entities = []
    for sensor in config[CONF_SENSORS]:
        entities.append(DovadoSensor(dovado, sensor))

    add_entities(entities, True)


class DovadoSensor(SensorEntity):
    """Representation of a Dovado sensor."""

    def __init__(self, data, sensor):
        """Initialize the sensor."""
        self._data = data
        self._attr_name = f"{data.name} {SENSORS[sensor][1]}"
        self._attr_icon = SENSORS[sensor][3]
        self._attr_unit_of_measurement = SENSORS[sensor][2]
        self._sensor = sensor

    def _compute_state(self):
        """Compute the state of the sensor."""
        state = self._data.state.get(SENSORS[self._sensor][0])
        if self._sensor == SENSOR_NETWORK:
            match = re.search(r"\((.+)\)", state)
            return match.group(1) if match else None
        if self._sensor == SENSOR_SIGNAL:
            try:
                return int(state.split()[0])
            except ValueError:
                return None
        if self._sensor == SENSOR_SMS_UNREAD:
            return int(state)
        if self._sensor in [SENSOR_UPLOAD, SENSOR_DOWNLOAD]:
            return round(float(state) / 1e6, 1)
        return state

    def update(self):
        """Update sensor values."""
        self._data.update()
        self._attr_state = self._compute_state()
        self._attr_extra_state_attributes = {
            k: v for k, v in self._data.state.items() if k not in ["date", "time"]
        }
