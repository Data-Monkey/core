"""Details about the built-in battery."""
import logging
import os

from batinfo import Batteries
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import ATTR_NAME, CONF_NAME, DEVICE_CLASS_BATTERY, PERCENTAGE
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

ATTR_PATH = "path"
ATTR_ALARM = "alarm"
ATTR_CAPACITY = "capacity"
ATTR_CAPACITY_LEVEL = "capacity_level"
ATTR_CYCLE_COUNT = "cycle_count"
ATTR_ENERGY_FULL = "energy_full"
ATTR_ENERGY_FULL_DESIGN = "energy_full_design"
ATTR_ENERGY_NOW = "energy_now"
ATTR_MANUFACTURER = "manufacturer"
ATTR_MODEL_NAME = "model_name"
ATTR_POWER_NOW = "power_now"
ATTR_SERIAL_NUMBER = "serial_number"
ATTR_STATUS = "status"
ATTR_VOLTAGE_MIN_DESIGN = "voltage_min_design"
ATTR_VOLTAGE_NOW = "voltage_now"

ATTR_HEALTH = "health"
ATTR_STATUS = "status"

CONF_BATTERY = "battery"
CONF_SYSTEM = "system"

DEFAULT_BATTERY = 1
DEFAULT_NAME = "Battery"
DEFAULT_PATH = "/sys/class/power_supply"
DEFAULT_SYSTEM = "linux"

SYSTEMS = ["android", "linux"]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_BATTERY, default=DEFAULT_BATTERY): cv.positive_int,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_SYSTEM, default=DEFAULT_SYSTEM): vol.In(SYSTEMS),
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Linux Battery sensor."""
    name = config.get(CONF_NAME)
    battery_id = config.get(CONF_BATTERY)
    system = config.get(CONF_SYSTEM)

    try:
        if system == "android":
            os.listdir(os.path.join(DEFAULT_PATH, "battery"))
        else:
            os.listdir(os.path.join(DEFAULT_PATH, f"BAT{battery_id}"))
    except FileNotFoundError:
        _LOGGER.error("No battery found")
        return False

    add_entities([LinuxBatterySensor(name, battery_id, system)], True)


class LinuxBatterySensor(SensorEntity):
    """Representation of a Linux Battery sensor."""

    _attr_device_class = DEVICE_CLASS_BATTERY
    _attr_unit_of_measurement = PERCENTAGE

    def __init__(self, name, battery_id, system):
        """Initialize the battery sensor."""
        self._battery = Batteries()

        self._attr_name = name
        self._battery_id = battery_id - 1
        self._system = system

    def update(self):
        """Get the latest data and updates the states."""
        self._battery.update()
        battery_stat = self._battery.stat[self._battery_id]
        self._attr_state = battery_stat.capacity
        if self._system == "android":
            self._attr_extra_state_attributes = {
                ATTR_NAME: battery_stat.name,
                ATTR_PATH: battery_stat.path,
                ATTR_HEALTH: battery_stat.health,
                ATTR_STATUS: battery_stat.status,
            }
        else:
            self._attr_extra_state_attributes = {
                ATTR_NAME: battery_stat.name,
                ATTR_PATH: battery_stat.path,
                ATTR_ALARM: battery_stat.alarm,
                ATTR_CAPACITY_LEVEL: battery_stat.capacity_level,
                ATTR_CYCLE_COUNT: battery_stat.cycle_count,
                ATTR_ENERGY_FULL: battery_stat.energy_full,
                ATTR_ENERGY_FULL_DESIGN: battery_stat.energy_full_design,
                ATTR_ENERGY_NOW: battery_stat.energy_now,
                ATTR_MANUFACTURER: battery_stat.manufacturer,
                ATTR_MODEL_NAME: battery_stat.model_name,
                ATTR_POWER_NOW: battery_stat.power_now,
                ATTR_SERIAL_NUMBER: battery_stat.serial_number,
                ATTR_STATUS: battery_stat.status,
                ATTR_VOLTAGE_MIN_DESIGN: battery_stat.voltage_min_design,
                ATTR_VOLTAGE_NOW: battery_stat.voltage_now,
            }
