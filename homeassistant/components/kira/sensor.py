"""KIRA interface to receive UDP packets from an IR-IP bridge."""
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_DEVICE, CONF_NAME

from . import CONF_SENSOR, DOMAIN

_LOGGER = logging.getLogger(__name__)

ICON = "mdi:remote"


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up a Kira sensor."""
    if discovery_info is not None:
        name = discovery_info.get(CONF_NAME)
        device = discovery_info.get(CONF_DEVICE)
        kira = hass.data[DOMAIN][CONF_SENSOR][name]

        add_entities([KiraReceiver(device, kira)])


class KiraReceiver(SensorEntity):
    """Implementation of a Kira Receiver."""

    _attr_force_update = True
    _attr_icon = ICON
    _attr_should_poll = False

    def __init__(self, name, kira):
        """Initialize the sensor."""
        self._attr_name = name

        kira.registerCallback(self._update_callback)

    def _update_callback(self, code):
        code_name, device = code
        _LOGGER.debug("Kira Code: %s", code_name)
        self._attr_state = code_name
        self._attr_extra_state_attributes = {CONF_DEVICE: device}
        self.schedule_update_ha_state()
