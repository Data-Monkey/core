"""Support for the Hive sensors."""

from datetime import timedelta

from homeassistant.components.sensor import DEVICE_CLASS_BATTERY, SensorEntity

from . import HiveEntity
from .const import DOMAIN

PARALLEL_UPDATES = 0
SCAN_INTERVAL = timedelta(seconds=15)
DEVICETYPE = {
    "Battery": {"unit": " % ", "type": DEVICE_CLASS_BATTERY},
}


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Hive thermostat based on a config entry."""

    hive = hass.data[DOMAIN][entry.entry_id]
    devices = hive.session.deviceList.get("sensor")
    entities = []
    if devices:
        for dev in devices:
            entities.append(HiveSensorEntity(hive, dev))
    async_add_entities(entities, True)


class HiveSensorEntity(HiveEntity, SensorEntity):
    """Hive Sensor Entity."""

    def __init__(self, hive, hive_device):
        """Initialize a Hive Sensor Entity."""
        super().__init__(hive, hive_device)
        self._attr_name = hive_device["haName"]
        self._attr_device_class = DEVICETYPE[hive_device["hiveType"]].get("type")
        self._attr_unit_of_measurement = DEVICETYPE[hive_device["hiveType"]].get("unit")
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
        self._attr_state = self.device["status"]["state"]
        self._attr_available = self.device.get("deviceData", {}).get("online")
