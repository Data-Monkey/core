"""Provides a sensor for Home Connect."""

from datetime import timedelta
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_ENTITIES, DEVICE_CLASS_TIMESTAMP
import homeassistant.util.dt as dt_util

from .const import ATTR_VALUE, BSH_OPERATION_STATE, DOMAIN
from .entity import HomeConnectEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Home Connect sensor."""

    def get_entities():
        """Get a list of entities."""
        entities = []
        hc_api = hass.data[DOMAIN][config_entry.entry_id]
        for device_dict in hc_api.devices:
            entity_dicts = device_dict.get(CONF_ENTITIES, {}).get("sensor", [])
            entities += [HomeConnectSensor(**d) for d in entity_dicts]
        return entities

    async_add_entities(await hass.async_add_executor_job(get_entities), True)


class HomeConnectSensor(HomeConnectEntity, SensorEntity):
    """Sensor class for Home Connect."""

    def __init__(self, device, desc, key, unit, icon, device_class, sign=1):
        """Initialize the entity."""
        super().__init__(device, desc)
        self._key = key
        self._attr_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_device_class = device_class
        self._sign = sign

    async def async_update(self):
        """Update the sensor's status."""
        status = self.device.appliance.status
        if self._key not in status:
            self._attr_state = None
        else:
            if self.device_class == DEVICE_CLASS_TIMESTAMP:
                if ATTR_VALUE not in status[self._key]:
                    self._attr_state = None
                elif (
                    self.state is not None
                    and self._sign == 1
                    and dt_util.parse_datetime(self.state) < dt_util.utcnow()
                ):
                    # if the date is supposed to be in the future but we're
                    # already past it, set state to None.
                    self._attr_state = None
                else:
                    seconds = self._sign * float(status[self._key][ATTR_VALUE])
                    self._attr_state = (
                        dt_util.utcnow() + timedelta(seconds=seconds)
                    ).isoformat()
            else:
                self._attr_state = status[self._key].get(ATTR_VALUE)
                if self._key == BSH_OPERATION_STATE:
                    # Value comes back as an enum, we only really care about the
                    # last part, so split it off
                    # https://developer.home-connect.com/docs/status/operation_state
                    self._attr_state = self.state.split(".")[-1]
        self._attr_available = self.state is not None
        _LOGGER.debug("Updated, new state: %s", self.state)
