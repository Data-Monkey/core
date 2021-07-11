"""Support for Enviro pHAT sensors."""
from datetime import timedelta
import importlib
import logging

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import (
    CONF_DISPLAY_OPTIONS,
    CONF_NAME,
    PRESSURE_HPA,
    TEMP_CELSIUS,
    VOLT,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "envirophat"
CONF_USE_LEDS = "use_leds"

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=60)

SENSOR_TYPES = {
    "light": ["light", " ", "mdi:weather-sunny"],
    "light_red": ["light_red", " ", "mdi:invert-colors"],
    "light_green": ["light_green", " ", "mdi:invert-colors"],
    "light_blue": ["light_blue", " ", "mdi:invert-colors"],
    "accelerometer_x": ["accelerometer_x", "G", "mdi:earth"],
    "accelerometer_y": ["accelerometer_y", "G", "mdi:earth"],
    "accelerometer_z": ["accelerometer_z", "G", "mdi:earth"],
    "magnetometer_x": ["magnetometer_x", " ", "mdi:magnet"],
    "magnetometer_y": ["magnetometer_y", " ", "mdi:magnet"],
    "magnetometer_z": ["magnetometer_z", " ", "mdi:magnet"],
    "temperature": ["temperature", TEMP_CELSIUS, "mdi:thermometer"],
    "pressure": ["pressure", PRESSURE_HPA, "mdi:gauge"],
    "voltage_0": ["voltage_0", VOLT, "mdi:flash"],
    "voltage_1": ["voltage_1", VOLT, "mdi:flash"],
    "voltage_2": ["voltage_2", VOLT, "mdi:flash"],
    "voltage_3": ["voltage_3", VOLT, "mdi:flash"],
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_DISPLAY_OPTIONS, default=list(SENSOR_TYPES)): [
            vol.In(SENSOR_TYPES)
        ],
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_USE_LEDS, default=False): cv.boolean,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Sense HAT sensor platform."""
    try:
        envirophat = importlib.import_module("envirophat")
    except OSError:
        _LOGGER.error("No Enviro pHAT was found")
        return False

    data = EnvirophatData(envirophat, config.get(CONF_USE_LEDS))

    dev = []
    for variable in config[CONF_DISPLAY_OPTIONS]:
        dev.append(EnvirophatSensor(data, variable))

    add_entities(dev, True)


class EnvirophatSensor(SensorEntity):
    """Representation of an Enviro pHAT sensor."""

    def __init__(self, data, sensor_types):
        """Initialize the sensor."""
        self.data = data
        self._attr_name = SENSOR_TYPES[sensor_types][0]
        self._attr_icon = SENSOR_TYPES[sensor_types][2]
        self._attr_unit_of_measurement = SENSOR_TYPES[sensor_types][1]
        self.type = sensor_types

    def update(self):
        """Get the latest data and updates the states."""
        self.data.update()

        if self.type == "light":
            self._attr_state = self.data.light
        elif self.type == "light_red":
            self._attr_state = self.data.light_red
        elif self.type == "light_green":
            self._attr_state = self.data.light_green
        elif self.type == "light_blue":
            self._attr_state = self.data.light_blue
        elif self.type == "accelerometer_x":
            self._attr_state = self.data.accelerometer_x
        elif self.type == "accelerometer_y":
            self._attr_state = self.data.accelerometer_y
        elif self.type == "accelerometer_z":
            self._attr_state = self.data.accelerometer_z
        elif self.type == "magnetometer_x":
            self._attr_state = self.data.magnetometer_x
        elif self.type == "magnetometer_y":
            self._attr_state = self.data.magnetometer_y
        elif self.type == "magnetometer_z":
            self._attr_state = self.data.magnetometer_z
        elif self.type == "temperature":
            self._attr_state = self.data.temperature
        elif self.type == "pressure":
            self._attr_state = self.data.pressure
        elif self.type == "voltage_0":
            self._attr_state = self.data.voltage_0
        elif self.type == "voltage_1":
            self._attr_state = self.data.voltage_1
        elif self.type == "voltage_2":
            self._attr_state = self.data.voltage_2
        elif self.type == "voltage_3":
            self._attr_state = self.data.voltage_3


class EnvirophatData:
    """Get the latest data and update."""

    def __init__(self, envirophat, use_leds):
        """Initialize the data object."""
        self.envirophat = envirophat
        self.use_leds = use_leds
        # sensors readings
        self.light = self.light_red = self.light_green = self.light_blue = None
        self.accelerometer_x = self.accelerometer_y = self.accelerometer_z = None
        self.magnetometer_x = self.magnetometer_y = self.magnetometer_z = None
        self.temperature = self.pressure = self.voltage_0 = None
        self.voltage_1 = self.voltage_2 = self.voltage_3 = None

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the latest data from Enviro pHAT."""
        # Light sensor reading: 16-bit integer
        self.light = self.envirophat.light.light()
        if self.use_leds:
            self.envirophat.leds.on()
        # the three color values scaled against the overall light, 0-255
        self.light_red, self.light_green, self.light_blue = self.envirophat.light.rgb()
        if self.use_leds:
            self.envirophat.leds.off()

        # accelerometer readings in G
        (
            self.accelerometer_x,
            self.accelerometer_y,
            self.accelerometer_z,
        ) = self.envirophat.motion.accelerometer()

        # raw magnetometer reading
        (
            self.magnetometer_x,
            self.magnetometer_y,
            self.magnetometer_z,
        ) = self.envirophat.motion.magnetometer()

        # temperature resolution of BMP280 sensor: 0.01°C
        self.temperature = round(self.envirophat.weather.temperature(), 2)

        # pressure resolution of BMP280 sensor: 0.16 Pa, rounding to 0.1 Pa
        # with conversion to 100 Pa = 1 hPa
        self.pressure = round(self.envirophat.weather.pressure() / 100.0, 3)

        # Voltage sensor, reading between 0-3.3V
        (
            self.voltage_0,
            self.voltage_1,
            self.voltage_2,
            self.voltage_3,
        ) = self.envirophat.analog.read_all()
