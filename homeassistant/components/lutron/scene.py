"""Support for Lutron scenes."""
from typing import Any

from homeassistant.components.scene import Scene

from . import LUTRON_DEVICES, LutronDevice


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Lutron scenes."""
    devs = []
    for scene_data in hass.data[LUTRON_DEVICES]["scene"]:
        (area_name, keypad_name, device, led) = scene_data
        dev = LutronScene(area_name, keypad_name, device, led)
        devs.append(dev)

    add_entities(devs, True)


class LutronScene(LutronDevice, Scene):
    """Representation of a Lutron Scene."""

    def __init__(self, area_name, keypad_name, lutron_device, lutron_led):
        """Initialize the scene/button."""
        super().__init__(area_name, lutron_device)
        self._keypad_name = keypad_name
        self._led = lutron_led
        self._attr_name = f"{area_name} {keypad_name}: {lutron_device.name}"

    def activate(self, **kwargs: Any) -> None:
        """Activate the scene."""
        self._lutron_device.press()
