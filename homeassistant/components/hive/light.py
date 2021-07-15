"""Support for Hive light devices."""
from datetime import timedelta

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_HS_COLOR,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR,
    SUPPORT_COLOR_TEMP,
    LightEntity,
)
import homeassistant.util.color as color_util

from . import HiveEntity, refresh_system
from .const import ATTR_MODE, DOMAIN

PARALLEL_UPDATES = 0
SCAN_INTERVAL = timedelta(seconds=15)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Hive thermostat based on a config entry."""

    hive = hass.data[DOMAIN][entry.entry_id]
    devices = hive.session.deviceList.get("light")
    entities = []
    if devices:
        for dev in devices:
            entities.append(HiveDeviceLight(hive, dev))
    async_add_entities(entities, True)


class HiveDeviceLight(HiveEntity, LightEntity):
    """Hive Active Light Device."""

    def __init__(self, hive, hive_device):
        """Initialize a Hive Active Light Device."""
        super().__init__(hive, hive_device)
        self._attr_name = hive_device["haName"]
        self._attr_max_mireds = hive_device.get("max_mireds")
        self._attr_min_mireds = hive_device.get("min_mireds")
        self._attr_supported_features = None
        if hive_device["hiveType"] == "warmwhitelight":
            self._attr_supported_features = SUPPORT_BRIGHTNESS
        elif hive_device["hiveType"] == "tuneablelight":
            self._attr_supported_features = SUPPORT_BRIGHTNESS | SUPPORT_COLOR_TEMP
        elif hive_device["hiveType"] == "colourtuneablelight":
            self._attr_supported_features = (
                SUPPORT_BRIGHTNESS | SUPPORT_COLOR_TEMP | SUPPORT_COLOR
            )
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
        """Instruct the light to turn on."""
        new_brightness = None
        new_color_temp = None
        new_color = None
        if ATTR_BRIGHTNESS in kwargs:
            tmp_new_brightness = kwargs.get(ATTR_BRIGHTNESS)
            percentage_brightness = (tmp_new_brightness / 255) * 100
            new_brightness = int(round(percentage_brightness / 5.0) * 5.0)
            if new_brightness == 0:
                new_brightness = 5
        if ATTR_COLOR_TEMP in kwargs:
            tmp_new_color_temp = kwargs.get(ATTR_COLOR_TEMP)
            new_color_temp = round(1000000 / tmp_new_color_temp)
        if ATTR_HS_COLOR in kwargs:
            get_new_color = kwargs.get(ATTR_HS_COLOR)
            hue = int(get_new_color[0])
            saturation = int(get_new_color[1])
            new_color = (hue, saturation, 100)

        await self.hive.light.turnOn(
            self.device, new_brightness, new_color_temp, new_color
        )

    @refresh_system
    async def async_turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        await self.hive.light.turnOff(self.device)

    async def async_update(self):
        """Update all Node data from Hive."""
        await self.hive.session.updateData(self.device)
        self.device = await self.hive.light.getLight(self.device)
        self.attributes.update(self.device.get("attributes", {}))
        self._attr_available = self.device["deviceData"]["online"]
        self._attr_extra_state_attributes = {
            ATTR_MODE: self.attributes.get(ATTR_MODE),
        }

        self._attr_hs_color = None
        if self.device["status"]["mode"] == "COLOUR":
            rgb = self.device["status"].get("hs_color")
            self._attr_hs_color = color_util.color_RGB_to_hs(*rgb)
        self._attr_brightness = self.device["status"]["brightness"]
        self._attr_color_temp = self.device["status"].get("color_temp")
