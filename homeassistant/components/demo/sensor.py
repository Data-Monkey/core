"""Demo platform that has a couple of fake sensors."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_IDENTIFIERS,
    ATTR_NAME,
    CONCENTRATION_PARTS_PER_MILLION,
    DEVICE_CLASS_CO,
    DEVICE_CLASS_CO2,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_TEMPERATURE,
    PERCENTAGE,
    TEMP_CELSIUS,
)

from . import DOMAIN


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Demo sensors."""
    async_add_entities(
        [
            DemoSensor(
                "sensor_1",
                "Outside Temperature",
                15.6,
                DEVICE_CLASS_TEMPERATURE,
                TEMP_CELSIUS,
                12,
            ),
            DemoSensor(
                "sensor_2",
                "Outside Humidity",
                54,
                DEVICE_CLASS_HUMIDITY,
                PERCENTAGE,
                None,
            ),
            DemoSensor(
                "sensor_3",
                "Carbon monoxide",
                54,
                DEVICE_CLASS_CO,
                CONCENTRATION_PARTS_PER_MILLION,
                None,
            ),
            DemoSensor(
                "sensor_4",
                "Carbon dioxide",
                54,
                DEVICE_CLASS_CO2,
                CONCENTRATION_PARTS_PER_MILLION,
                14,
            ),
        ]
    )


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Demo config entry."""
    await async_setup_platform(hass, {}, async_add_entities)


class DemoSensor(SensorEntity):
    """Representation of a Demo sensor."""

    def __init__(
        self, unique_id, name, state, device_class, unit_of_measurement, battery
    ):
        """Initialize the sensor."""
        self._unique_id = unique_id
        self._name = name
        self._state = state
        self._device_class = device_class
        self._unit_of_measurement = unit_of_measurement
        self._battery = battery

    @property
    def device_info(self):
        """Return device info."""
        return {
            ATTR_IDENTIFIERS: {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.unique_id)
            },
            ATTR_NAME: self.name,
        }

    @property
    def unique_id(self):
        """Return the unique id."""
        return self._unique_id

    @property
    def should_poll(self):
        """No polling needed for a demo sensor."""
        return False

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return self._device_class

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return self._unit_of_measurement

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if self._battery:
            return {ATTR_BATTERY_LEVEL: self._battery}
