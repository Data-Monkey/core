"""Support for Kaiterra Temperature ahn Humidity Sensors."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_NAME,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_TEMPERATURE,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DISPATCHER_KAITERRA, DOMAIN

SENSORS = [
    {"name": "Temperature", "prop": "rtemp", "device_class": DEVICE_CLASS_TEMPERATURE},
    {"name": "Humidity", "prop": "rhumid", "device_class": DEVICE_CLASS_HUMIDITY},
]


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the kaiterra temperature and humidity sensor."""
    if discovery_info is None:
        return

    api = hass.data[DOMAIN]
    name = discovery_info[CONF_NAME]
    device_id = discovery_info[CONF_DEVICE_ID]

    async_add_entities(
        [KaiterraSensor(api, name, device_id, sensor) for sensor in SENSORS]
    )


class KaiterraSensor(SensorEntity):
    """Implementation of a Kaittera sensor."""

    _attr_should_poll = False

    def __init__(self, api, name, device_id, sensor):
        """Initialize the sensor."""
        self._api = api
        self._attr_name = f'{name} {sensor["name"]}'
        self._attr_unique_id = f"{device_id}_{sensor['name'].lower()}"
        self._device_id = device_id
        self._property = sensor["prop"]
        self._attr_device_class = sensor["device_class"]
        if self._sensor.get("units"):
            value = self._sensor["units"].value
            self._attr_unit_of_measurement = value
            if value == "F":
                self._attr_unit_of_measurement = TEMP_FAHRENHEIT
            elif value == "C":
                self._attr_unit_of_measurement = TEMP_CELSIUS

    @property
    def _sensor(self):
        """Return the sensor data."""
        return self._api.data.get(self._device_id, {}).get(self._property, {})

    @property
    def available(self):
        """Return the availability of the sensor."""
        return self._api.data.get(self._device_id) is not None

    @property
    def state(self):
        """Return the state."""
        return self._sensor.get("value")

    async def async_added_to_hass(self):
        """Register callback."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, DISPATCHER_KAITERRA, self.async_write_ha_state
            )
        )
