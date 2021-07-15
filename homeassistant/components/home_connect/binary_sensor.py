"""Provides a binary sensor for Home Connect."""
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import CONF_ENTITIES

from .const import (
    ATTR_VALUE,
    BSH_DOOR_STATE,
    BSH_DOOR_STATE_CLOSED,
    BSH_DOOR_STATE_LOCKED,
    BSH_DOOR_STATE_OPEN,
    BSH_REMOTE_CONTROL_ACTIVATION_STATE,
    BSH_REMOTE_START_ALLOWANCE_STATE,
    DOMAIN,
)
from .entity import HomeConnectEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Home Connect binary sensor."""

    def get_entities():
        entities = []
        hc_api = hass.data[DOMAIN][config_entry.entry_id]
        for device_dict in hc_api.devices:
            entity_dicts = device_dict.get(CONF_ENTITIES, {}).get("binary_sensor", [])
            entities += [HomeConnectBinarySensor(**d) for d in entity_dicts]
        return entities

    async_add_entities(await hass.async_add_executor_job(get_entities), True)


class HomeConnectBinarySensor(HomeConnectEntity, BinarySensorEntity):
    """Binary sensor for Home Connect."""

    def __init__(self, device, desc, sensor_type, device_class=None):
        """Initialize the entity."""
        super().__init__(device, desc)
        self._attr_device_class = device_class
        self._type = sensor_type
        if sensor_type == "door":
            self._update_key = BSH_DOOR_STATE
            self._false_value_list = (BSH_DOOR_STATE_CLOSED, BSH_DOOR_STATE_LOCKED)
            self._true_value_list = [BSH_DOOR_STATE_OPEN]
        elif sensor_type == "remote_control":
            self._update_key = BSH_REMOTE_CONTROL_ACTIVATION_STATE
            self._false_value_list = [False]
            self._true_value_list = [True]
        elif sensor_type == "remote_start":
            self._update_key = BSH_REMOTE_START_ALLOWANCE_STATE
            self._false_value_list = [False]
            self._true_value_list = [True]

    async def async_update(self):
        """Update the binary sensor's status."""
        state = self.device.appliance.status.get(self._update_key, {})
        if not state:
            self._attr_is_on = None
        elif state.get(ATTR_VALUE) in self._false_value_list:
            self._attr_is_on = False
        elif state.get(ATTR_VALUE) in self._true_value_list:
            self._attr_is_on = True
        else:
            _LOGGER.warning(
                "Unexpected value for HomeConnect %s state: %s", self._type, state
            )
            self._attr_is_on = None
        self._attr_available = self.is_on is not None
        _LOGGER.debug("Updated, new state: %s", self.is_on)
