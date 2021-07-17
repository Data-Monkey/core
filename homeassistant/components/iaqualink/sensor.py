"""Support for Aqualink temperature sensors."""
from __future__ import annotations

from iaqualink.device import AqualinkDevice

from homeassistant.components.sensor import DOMAIN, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import DEVICE_CLASS_TEMPERATURE, TEMP_CELSIUS, TEMP_FAHRENHEIT
from homeassistant.core import HomeAssistant

from . import AqualinkEntity
from .const import DOMAIN as AQUALINK_DOMAIN

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
) -> None:
    """Set up discovered sensors."""
    devs = []
    for dev in hass.data[AQUALINK_DOMAIN][DOMAIN]:
        devs.append(HassAqualinkSensor(dev))
    async_add_entities(devs, True)


class HassAqualinkSensor(AqualinkEntity, SensorEntity):
    """Representation of a sensor."""

    def __init__(self, dev: AqualinkDevice) -> None:
        """Initialize a sensor."""
        super().__init__(dev)
        self._attr_name = dev.label
        if dev.name.endswith("_temp"):
            self._attr_unit_of_measurement = TEMP_CELSIUS
            if dev.system.temp_unit == "F":
                self._attr_unit_of_measurement = TEMP_FAHRENHEIT
        if dev.name.endswith("_temp"):
            self._attr_device_class = DEVICE_CLASS_TEMPERATURE

    @property
    def state(self) -> str | None:
        """Return the state of the sensor."""
        if self.dev.state == "":
            return None

        try:
            state = int(self.dev.state)
        except ValueError:
            state = float(self.dev.state)
        return state
