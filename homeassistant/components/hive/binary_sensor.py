"""Support for the Hive binary sensors."""
from datetime import timedelta

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_CONNECTIVITY,
    DEVICE_CLASS_MOTION,
    DEVICE_CLASS_OPENING,
    DEVICE_CLASS_SMOKE,
    DEVICE_CLASS_SOUND,
    BinarySensorEntity,
)

from . import HiveEntity
from .const import ATTR_MODE, DOMAIN

DEVICETYPE = {
    "contactsensor": DEVICE_CLASS_OPENING,
    "motionsensor": DEVICE_CLASS_MOTION,
    "Connectivity": DEVICE_CLASS_CONNECTIVITY,
    "SMOKE_CO": DEVICE_CLASS_SMOKE,
    "DOG_BARK": DEVICE_CLASS_SOUND,
    "GLASS_BREAK": DEVICE_CLASS_SOUND,
}
PARALLEL_UPDATES = 0
SCAN_INTERVAL = timedelta(seconds=15)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Hive thermostat based on a config entry."""

    hive = hass.data[DOMAIN][entry.entry_id]
    devices = hive.session.deviceList.get("binary_sensor")
    entities = []
    if devices:
        for dev in devices:
            entities.append(HiveBinarySensorEntity(hive, dev))
    async_add_entities(entities, True)


class HiveBinarySensorEntity(HiveEntity, BinarySensorEntity):
    """Representation of a Hive binary sensor."""

    def __init__(self, hive, hive_device):
        """Initialize a Hive binary sensor."""
        super().__init__(hive, hive_device)
        self._attr_name = hive_device["haName"]
        self._attr_device_class = DEVICETYPE.get(hive_device["hiveType"])
        self._attr_device_info = {
            "identifiers": {(DOMAIN, hive_device["device_id"])},
            "name": hive_device["device_name"],
            "model": hive_device["deviceData"]["model"],
            "manufacturer": hive_device["deviceData"]["manufacturer"],
            "sw_version": hive_device["deviceData"]["version"],
            "via_device": (DOMAIN, hive_device["parentDevice"]),
        }

    async def async_update(self):
        """Update all Node data from Hive."""
        await self.hive.session.updateData(self.device)
        self.device = await self.hive.sensor.getSensor(self.device)
        self.attributes = self.device.get("attributes", {})
        self._attr_is_on = self.device["status"]["state"]
        self._attr_available = True
        if self.device["hiveType"] != "Connectivity":
            self._attr_available = self.device["deviceData"]["online"]
        self._attr_extra_state_attributes = {
            ATTR_MODE: self.attributes.get(ATTR_MODE),
        }
