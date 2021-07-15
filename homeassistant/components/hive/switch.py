"""Support for the Hive switches."""
from datetime import timedelta

from homeassistant.components.switch import SwitchEntity

from . import HiveEntity, refresh_system
from .const import ATTR_MODE, DOMAIN

PARALLEL_UPDATES = 0
SCAN_INTERVAL = timedelta(seconds=15)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Hive thermostat based on a config entry."""

    hive = hass.data[DOMAIN][entry.entry_id]
    devices = hive.session.deviceList.get("switch")
    entities = []
    if devices:
        for dev in devices:
            entities.append(HiveDevicePlug(hive, dev))
    async_add_entities(entities, True)


class HiveDevicePlug(HiveEntity, SwitchEntity):
    """Hive Active Plug."""

    def __init__(self, hive, hive_device):
        """Initialize a Hive Active Plug."""
        super().__init__(hive, hive_device)
        self._attr_name = hive_device["haName"]
        if hive_device["hiveType"] == "activeplug":
            self._attr_device_info = {
                "identifiers": {(DOMAIN, hive_device["device_id"])},
                "name": hive_device["device_name"],
                "model": hive_device["deviceData"]["model"],
                "manufacturer": hive_device["deviceData"]["manufacturer"],
                "sw_version": hive_device["deviceData"]["version"],
                "via_device": (DOMAIN, hive_device["parentDevice"]),
            }

    @refresh_system
    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        await self.hive.switch.turnOn(self.device)

    @refresh_system
    async def async_turn_off(self, **kwargs):
        """Turn the device off."""
        await self.hive.switch.turnOff(self.device)

    async def async_update(self):
        """Update all Node data from Hive."""
        await self.hive.session.updateData(self.device)
        self.device = await self.hive.switch.getSwitch(self.device)
        self.attributes.update(self.device.get("attributes", {}))
        self._attr_available = self.device["deviceData"].get("online")
        self._attr_is_on = self.device["status"]["state"]
        self._attr_extra_state_attributes = {
            ATTR_MODE: self.attributes.get(ATTR_MODE),
        }
        self._attr_current_power_w = self.device["status"].get("power_usage")
