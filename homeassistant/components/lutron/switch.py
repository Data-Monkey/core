"""Support for Lutron switches."""
from homeassistant.components.switch import SwitchEntity

from . import LUTRON_DEVICES, LutronDevice


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Lutron switches."""
    devs = []

    # Add Lutron Switches
    for (area_name, device) in hass.data[LUTRON_DEVICES]["switch"]:
        dev = LutronSwitch(area_name, device)
        devs.append(dev)

    # Add the indicator LEDs for scenes (keypad buttons)
    for scene_data in hass.data[LUTRON_DEVICES]["scene"]:
        (area_name, keypad_name, scene, led) = scene_data
        if led is not None:
            led = LutronLed(area_name, keypad_name, scene, led)
            devs.append(led)

    add_entities(devs, True)


class LutronSwitch(LutronDevice, SwitchEntity):
    """Representation of a Lutron Switch."""

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        self._lutron_device.level = 100

    def turn_off(self, **kwargs):
        """Turn the switch off."""
        self._lutron_device.level = 0

    def update(self):
        """Call when forcing a refresh of the device."""
        self._attr_is_on = self._lutron_device.last_level() > 0
        self._attr_extra_state_attributes = {
            "lutron_integration_id": self._lutron_device.id
        }


class LutronLed(LutronDevice, SwitchEntity):
    """Representation of a Lutron Keypad LED."""

    def __init__(self, area_name, keypad_name, scene_device, led_device):
        """Initialize the switch."""
        super().__init__(area_name, led_device)
        self._keypad_name = keypad_name
        self._scene_name = scene_device.name
        self._attr_name = f"{area_name} {keypad_name}: {scene_device.name} LED"

    def turn_on(self, **kwargs):
        """Turn the LED on."""
        self._lutron_device.state = 1

    def turn_off(self, **kwargs):
        """Turn the LED off."""
        self._lutron_device.state = 0

    def update(self):
        """Call when forcing a refresh of the device."""
        if self._lutron_device.last_state is not None:
            self._attr_is_on = self._lutron_device.last_state
            return

        # The following property getter actually triggers an update in Lutron
        self._lutron_device.state  # pylint: disable=pointless-statement

        self._attr_extra_state_attributes = {
            "keypad": self._keypad_name,
            "scene": self._scene_name,
            "led": self._lutron_device.name,
        }
