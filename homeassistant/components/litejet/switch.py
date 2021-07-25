"""Support for LiteJet switch."""
import logging

from homeassistant.components.switch import SwitchEntity

from .const import DOMAIN

ATTR_NUMBER = "number"

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up entry."""

    system = hass.data[DOMAIN]

    def get_entities(system):
        entities = []
        for i in system.button_switches():
            name = system.get_switch_name(i)
            entities.append(LiteJetSwitch(config_entry.entry_id, system, i, name))
        return entities

    async_add_entities(await hass.async_add_executor_job(get_entities, system), True)


class LiteJetSwitch(SwitchEntity):
    """Representation of a single LiteJet switch."""

    _attr_entity_registry_enabled_default = False
    _attr_should_poll = False

    def __init__(self, entry_id, lj, i, name):
        """Initialize a LiteJet switch."""
        self._lj = lj
        self._index = i
        self._attr_is_on = False
        self._attr_name = name
        self._attr_unique_id = f"{entry_id}_{i}"
        self._attr_extra_state_attributes = {ATTR_NUMBER: i}

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""
        self._lj.on_switch_pressed(self._index, self._on_switch_pressed)
        self._lj.on_switch_released(self._index, self._on_switch_released)

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        self._lj.unsubscribe(self._on_switch_pressed)
        self._lj.unsubscribe(self._on_switch_released)

    def _on_switch_pressed(self):
        _LOGGER.debug("Updating pressed for %s", self.name)
        self._attr_is_on = True
        self.schedule_update_ha_state()

    def _on_switch_released(self):
        _LOGGER.debug("Updating released for %s", self.name)
        self._attr_is_on = False
        self.schedule_update_ha_state()

    def turn_on(self, **kwargs):
        """Press the switch."""
        self._lj.press_switch(self._index)

    def turn_off(self, **kwargs):
        """Release the switch."""
        self._lj.release_switch(self._index)
