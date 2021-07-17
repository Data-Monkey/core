"""Support for Aqualink pool feature switches."""
from iaqualink.device import AqualinkDevice

from homeassistant.components.switch import DOMAIN, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import AqualinkEntity, refresh_system
from .const import DOMAIN as AQUALINK_DOMAIN

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
) -> None:
    """Set up discovered switches."""
    devs = []
    for dev in hass.data[AQUALINK_DOMAIN][DOMAIN]:
        devs.append(HassAqualinkSwitch(dev))
    async_add_entities(devs, True)


class HassAqualinkSwitch(AqualinkEntity, SwitchEntity):
    """Representation of a switch."""

    def __init__(self, dev: AqualinkDevice) -> None:
        """Initialize a switch."""
        super().__init__(dev)
        self._attr_name = dev.label
        if self.name == "Cleaner":
            self._attr_icon = "mdi:robot-vacuum"
        elif self.name == "Waterfall" or self.name.endswith("Dscnt"):
            self._attr_icon = "mdi:fountain"
        elif self.name.endswith("Pump") or self.name.endswith("Blower"):
            self._attr_icon = "mdi:fan"
        elif self.name.endswith("Heater"):
            self._attr_icon = "mdi:radiator"

    @property
    def is_on(self) -> bool:
        """Return whether the switch is on or not."""
        return self.dev.is_on

    @refresh_system
    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the switch."""
        await self.dev.turn_on()

    @refresh_system
    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the switch."""
        await self.dev.turn_off()
