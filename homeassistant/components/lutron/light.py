"""Support for Lutron lights."""
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    SUPPORT_BRIGHTNESS,
    LightEntity,
)

from . import LUTRON_DEVICES, LutronDevice


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Lutron lights."""
    devs = []
    for (area_name, device) in hass.data[LUTRON_DEVICES]["light"]:
        dev = LutronLight(area_name, device)
        devs.append(dev)

    add_entities(devs, True)


def to_lutron_level(level):
    """Convert the given Home Assistant light level (0-255) to Lutron (0.0-100.0)."""
    return float((level * 100) / 255)


def to_hass_level(level):
    """Convert the given Lutron (0.0-100.0) light level to Home Assistant (0-255)."""
    return int((level * 255) / 100)


class LutronLight(LutronDevice, LightEntity):
    """Representation of a Lutron Light, including dimmable."""

    _attr_supported_features = SUPPORT_BRIGHTNESS

    def __init__(self, area_name, lutron_device):
        """Initialize the light."""
        self._prev_brightness = None
        super().__init__(area_name, lutron_device)

    def turn_on(self, **kwargs):
        """Turn the light on."""
        if ATTR_BRIGHTNESS in kwargs and self._lutron_device.is_dimmable:
            brightness = kwargs[ATTR_BRIGHTNESS]
        elif self._prev_brightness == 0:
            brightness = 255 / 2
        else:
            brightness = self._prev_brightness
        self._prev_brightness = brightness
        self._lutron_device.level = to_lutron_level(brightness)

    def turn_off(self, **kwargs):
        """Turn the light off."""
        self._lutron_device.level = 0

    def update(self):
        """Call when forcing a refresh of the device."""
        if self._prev_brightness is None:
            self._prev_brightness = to_hass_level(self._lutron_device.level)
        self._attr_is_on = self._lutron_device.last_level() > 0
        self._attr_extra_state_attributes = {
            "lutron_integration_id": self._lutron_device.id
        }
        self._attr_brightness = to_hass_level(self._lutron_device.last_level())
        if self.brightness != 0:
            self._prev_brightness = self.brightness
