"""Support for the KIWI.KI lock platform."""
import logging

from kiwiki import KiwiClient, KiwiException
import voluptuous as vol

from homeassistant.components.lock import PLATFORM_SCHEMA, LockEntity
from homeassistant.const import (
    ATTR_ID,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_call_later

_LOGGER = logging.getLogger(__name__)

ATTR_TYPE = "hardware_type"
ATTR_PERMISSION = "permission"
ATTR_CAN_INVITE = "can_invite_others"

UNLOCK_MAINTAIN_TIME = 5

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Required(CONF_USERNAME): cv.string, vol.Required(CONF_PASSWORD): cv.string}
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the KIWI lock platform."""

    try:
        kiwi = KiwiClient(config[CONF_USERNAME], config[CONF_PASSWORD])
    except KiwiException as exc:
        _LOGGER.error(exc)
        return
    available_locks = kiwi.get_locks()
    if not available_locks:
        # No locks found; abort setup routine.
        _LOGGER.info("No KIWI locks found in your account")
        return
    add_entities([KiwiLock(lock, kiwi) for lock in available_locks], True)


class KiwiLock(LockEntity):
    """Representation of a Kiwi lock."""

    def __init__(self, kiwi_lock, client):
        """Initialize the lock."""
        specifier = kiwi_lock["address"].get("specifier")
        self._attr_name = kiwi_lock.get("name") or specifier
        self._client = client
        self.lock_id = kiwi_lock["sensor_id"]
        self._attr_is_locked = True

        address = kiwi_lock.get("address")
        address.update(
            {
                ATTR_LATITUDE: address.pop("lat", None),
                ATTR_LONGITUDE: address.pop("lng", None),
            }
        )

        self._attr_extra_state_attributes = {
            ATTR_ID: kiwi_lock["sensor_id"],
            ATTR_TYPE: kiwi_lock.get("hardware_type"),
            ATTR_PERMISSION: kiwi_lock.get("highest_permission"),
            ATTR_CAN_INVITE: kiwi_lock.get("can_invite"),
            **address,
        }

    @callback
    def clear_unlock_state(self, _):
        """Clear unlock state automatically."""
        self._attr_is_locked = True
        self.async_write_ha_state()

    def unlock(self, **kwargs):
        """Unlock the device."""

        try:
            self._client.open_door(self.lock_id)
        except KiwiException:
            _LOGGER.error("Failed to open door")
        else:
            self._attr_is_locked = False
            self.hass.add_job(
                async_call_later,
                self.hass,
                UNLOCK_MAINTAIN_TIME,
                self.clear_unlock_state,
            )
