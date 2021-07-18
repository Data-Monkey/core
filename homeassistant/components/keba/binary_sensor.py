"""Support for KEBA charging station binary sensors."""
from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_CONNECTIVITY,
    DEVICE_CLASS_PLUG,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_SAFETY,
    BinarySensorEntity,
)

from . import DOMAIN


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the KEBA charging station platform."""
    if discovery_info is None:
        return

    keba = hass.data[DOMAIN]

    sensors = [
        KebaBinarySensor(
            keba, "Online", "Status", "device_state", DEVICE_CLASS_CONNECTIVITY
        ),
        KebaBinarySensor(keba, "Plug", "Plug", "plug_state", DEVICE_CLASS_PLUG),
        KebaBinarySensor(
            keba, "State", "Charging State", "charging_state", DEVICE_CLASS_POWER
        ),
        KebaBinarySensor(
            keba, "Tmo FS", "Failsafe Mode", "failsafe_mode_state", DEVICE_CLASS_SAFETY
        ),
    ]
    async_add_entities(sensors)


class KebaBinarySensor(BinarySensorEntity):
    """Representation of a binary sensor of a KEBA charging station."""

    _attr_should_poll = False

    def __init__(self, keba, key, name, entity_type, device_class):
        """Initialize the KEBA Sensor."""
        self._key = key
        self._keba = keba
        self._attr_name = f"{keba.device_name} {name}"
        self._attr_unique_id = f"{keba.device_id}_{entity_type}"
        self._attr_device_class = device_class
        self._attr_extra_state_attributes = {}

    async def async_update(self):
        """Get latest cached states from the device."""
        if self._key == "Online":
            self._attr_is_on = self._keba.get_value(self._key)

        elif self._key == "Plug":
            self._attr_is_on = self._keba.get_value("Plug_plugged")
            self._attr_extra_state_attributes[
                "plugged_on_wallbox"
            ] = self._keba.get_value("Plug_wallbox")
            self._attr_extra_state_attributes["plug_locked"] = self._keba.get_value(
                "Plug_locked"
            )
            self._attr_extra_state_attributes["plugged_on_EV"] = self._keba.get_value(
                "Plug_EV"
            )

        elif self._key == "State":
            self._attr_is_on = self._keba.get_value("State_on")
            self._attr_extra_state_attributes["status"] = self._keba.get_value(
                "State_details"
            )
            self._attr_extra_state_attributes["max_charging_rate"] = str(
                self._keba.get_value("Max curr")
            )

        elif self._key == "Tmo FS":
            self._attr_is_on = not self._keba.get_value("FS_on")
            self._attr_extra_state_attributes["failsafe_timeout"] = str(
                self._keba.get_value("Tmo FS")
            )
            self._attr_extra_state_attributes["fallback_current"] = str(
                self._keba.get_value("Curr FS")
            )
        elif self._key == "Authreq":
            self._attr_is_on = self._keba.get_value(self._key) == 0

    def update_callback(self):
        """Schedule a state update."""
        self.async_schedule_update_ha_state(True)

    async def async_added_to_hass(self):
        """Add update callback after being added to hass."""
        self._keba.add_update_listener(self.update_callback)
