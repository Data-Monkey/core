"""Support for Lutron shades."""
import logging

from homeassistant.components.cover import (
    ATTR_POSITION,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_SET_POSITION,
    CoverEntity,
)

from . import LUTRON_DEVICES, LutronDevice

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Lutron shades."""
    devs = []
    for (area_name, device) in hass.data[LUTRON_DEVICES]["cover"]:
        dev = LutronCover(area_name, device)
        devs.append(dev)

    add_entities(devs, True)
    return True


class LutronCover(LutronDevice, CoverEntity):
    """Representation of a Lutron shade."""

    _attr_supported_features = SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_SET_POSITION

    def close_cover(self, **kwargs):
        """Close the cover."""
        self._lutron_device.level = 0

    def open_cover(self, **kwargs):
        """Open the cover."""
        self._lutron_device.level = 100

    def set_cover_position(self, **kwargs):
        """Move the shade to a specific position."""
        if ATTR_POSITION in kwargs:
            position = kwargs[ATTR_POSITION]
            self._lutron_device.level = position

    def update(self):
        """Call when forcing a refresh of the device."""
        # Reading the property (rather than last_level()) fetches value
        level = self._lutron_device.level
        _LOGGER.debug("Lutron ID: %d updated to %f", self._lutron_device.id, level)
        self._attr_current_cover_position = self._lutron_device.last_level()
        self._attr_is_closed = self.current_cover_position < 1
        self._attr_extra_state_attributes = {
            "lutron_integration_id": self._lutron_device.id
        }
