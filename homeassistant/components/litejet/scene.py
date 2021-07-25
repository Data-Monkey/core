"""Support for LiteJet scenes."""
import logging
from typing import Any

from homeassistant.components.scene import Scene

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ATTR_NUMBER = "number"


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up entry."""

    system = hass.data[DOMAIN]

    def get_entities(system):
        entities = []
        for i in system.scenes():
            name = system.get_scene_name(i)
            entities.append(LiteJetScene(config_entry.entry_id, system, i, name))
        return entities

    async_add_entities(await hass.async_add_executor_job(get_entities, system), True)


class LiteJetScene(Scene):
    """Representation of a single LiteJet scene."""

    _attr_entity_registry_enabled_default = False

    def __init__(self, entry_id, lj, i, name):
        """Initialize the scene."""
        self._lj = lj
        self._index = i
        self._attr_name = name
        self._attr_unique_id = f"{entry_id}_{i}"
        self._attr_extra_state_attributes = {ATTR_NUMBER: i}

    def activate(self, **kwargs: Any) -> None:
        """Activate the scene."""
        self._lj.activate_scene(self._index)
