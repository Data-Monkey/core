"""Support for Lagute LW-12 WiFi LED Controller."""

import logging

import lw12
import voluptuous as vol

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ATTR_TRANSITION,
    PLATFORM_SCHEMA,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR,
    SUPPORT_EFFECT,
    SUPPORT_TRANSITION,
    LightEntity,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
import homeassistant.helpers.config_validation as cv
import homeassistant.util.color as color_util

_LOGGER = logging.getLogger(__name__)


DEFAULT_NAME = "LW-12 FC"
DEFAULT_PORT = 5000

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up LW-12 WiFi LED Controller platform."""
    # Assign configuration variables.
    name = config.get(CONF_NAME)
    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)
    # Add devices
    lw12_light = lw12.LW12Controller(host, port)
    add_entities([LW12WiFi(name, lw12_light)])


class LW12WiFi(LightEntity):
    """LW-12 WiFi LED Controller."""

    _attr_assumed_state = True
    _attr_effect_list = [
        effect.name.replace("_", " ").title() for effect in lw12.LW12_EFFECT
    ]
    _attr_should_poll = False
    _attr_supported_features = (
        SUPPORT_BRIGHTNESS | SUPPORT_EFFECT | SUPPORT_COLOR | SUPPORT_TRANSITION
    )

    def __init__(self, name, lw12_light):
        """Initialise LW-12 WiFi LED Controller.

        :param name: Friendly name for this platform to use.
        :param lw12_light: Instance of the LW12 controller.
        """
        self._light = lw12_light
        self._attr_name = name
        self._attr_hs_color = color_util.color_RGB_to_hs(*[255, 255, 255])
        self._attr_brightness = 255

    def turn_on(self, **kwargs):
        """Instruct the light to turn on."""
        self._light.light_on()
        if ATTR_HS_COLOR in kwargs:
            rgb_color = color_util.color_hs_to_RGB(*kwargs[ATTR_HS_COLOR])
            self._attr_hs_color = color_util.color_RGB_to_hs(*rgb_color)
            self._light.set_color(*rgb_color)
            self._attr_effect = None
        if ATTR_BRIGHTNESS in kwargs:
            self._attr_brightness = kwargs.get(ATTR_BRIGHTNESS)
            brightness = int(self.brightness / 255 * 100)
            self._light.set_light_option(lw12.LW12_LIGHT.BRIGHTNESS, brightness)
        if ATTR_EFFECT in kwargs:
            self._attr_effect = kwargs[ATTR_EFFECT].replace(" ", "_").upper()
            self._attr_effect.replace("_", " ").title()
            # Check if a known and supported effect was selected.
            if self.effect in [eff.name for eff in lw12.LW12_EFFECT]:
                # Selected effect is supported and will be applied.
                self._light.set_effect(lw12.LW12_EFFECT[self.effect])
            else:
                # Unknown effect was set, recover by disabling the effect
                # mode and log an error.
                _LOGGER.error("Unknown effect selected: %s", self.effect)
                self._attr_effect = None
        if ATTR_TRANSITION in kwargs:
            transition_speed = int(kwargs[ATTR_TRANSITION])
            self._light.set_light_option(lw12.LW12_LIGHT.FLASH, transition_speed)
        self._attr_is_on = True

    def turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        self._light.light_off()
        self._attr_is_on = False
