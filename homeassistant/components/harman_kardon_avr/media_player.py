"""Support for interface with an Harman/Kardon or JBL AVR."""
import hkavr
import voluptuous as vol

from homeassistant.components.media_player import PLATFORM_SCHEMA, MediaPlayerEntity
from homeassistant.components.media_player.const import (
    SUPPORT_SELECT_SOURCE,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_STEP,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, STATE_OFF, STATE_ON
import homeassistant.helpers.config_validation as cv

DEFAULT_NAME = "Harman Kardon AVR"
DEFAULT_PORT = 10025

SUPPORT_HARMAN_KARDON_AVR = (
    SUPPORT_VOLUME_STEP
    | SUPPORT_VOLUME_MUTE
    | SUPPORT_TURN_OFF
    | SUPPORT_TURN_ON
    | SUPPORT_SELECT_SOURCE
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    }
)


def setup_platform(hass, config, add_entities, discover_info=None):
    """Set up the AVR platform."""
    name = config[CONF_NAME]
    host = config[CONF_HOST]
    port = config[CONF_PORT]

    avr = hkavr.HkAVR(host, port, name)
    avr_device = HkAvrDevice(avr)

    add_entities([avr_device], True)


class HkAvrDevice(MediaPlayerEntity):
    """Representation of a Harman Kardon AVR / JBL AVR TV."""

    _attr_supported_features = SUPPORT_HARMAN_KARDON_AVR

    def __init__(self, avr):
        """Initialize a new HarmanKardonAVR."""
        self._avr = avr
        self._attr_name = avr.name
        self._attr_source_list = avr.sources
        self._attr_is_volume_muted = avr.muted
        self._attr_source = avr.current_source

    def update(self):
        """Update the state of this media_player."""
        if self._avr.is_on():
            self._attr_state = STATE_ON
        elif self._avr.is_off():
            self._attr_state = STATE_OFF
        else:
            self._attr_state = None

        self._attr_is_volume_muted = self._avr.muted
        self._attr_source = self._avr.current_source

    def turn_on(self):
        """Turn the AVR on."""
        self._avr.power_on()

    def turn_off(self):
        """Turn off the AVR."""
        self._avr.power_off()

    def select_source(self, source):
        """Select input source."""
        return self._avr.select_source(source)

    def volume_up(self):
        """Volume up the AVR."""
        return self._avr.volume_up()

    def volume_down(self):
        """Volume down AVR."""
        return self._avr.volume_down()

    def mute_volume(self, mute):
        """Send mute command."""
        return self._avr.mute(mute)
