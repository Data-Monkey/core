"""Support for Aqualink temperature sensors."""
from iaqualink.device import AqualinkDevice

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_COLD,
    DOMAIN,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import AqualinkEntity
from .const import DOMAIN as AQUALINK_DOMAIN

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
) -> None:
    """Set up discovered binary sensors."""
    devs = []
    for dev in hass.data[AQUALINK_DOMAIN][DOMAIN]:
        devs.append(HassAqualinkBinarySensor(dev))
    async_add_entities(devs, True)


class HassAqualinkBinarySensor(AqualinkEntity, BinarySensorEntity):
    """Representation of a binary sensor."""

    def __init__(self, dev: AqualinkDevice) -> None:
        """Initialize a binary sensor."""
        super().__init__(dev)
        self._attr_name = dev.label
        if self.name == "Freeze Protection":
            self._attr_device_class = DEVICE_CLASS_COLD

    @property
    def is_on(self) -> bool:
        """Return whether the binary sensor is on or not."""
        return self.dev.is_on
