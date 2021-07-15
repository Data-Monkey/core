"""Base for Hass.io entities."""
from __future__ import annotations

from typing import Any

from homeassistant.const import ATTR_NAME
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN, HassioDataUpdateCoordinator
from .const import ATTR_SLUG


class HassioAddonEntity(CoordinatorEntity):
    """Base entity for a Hass.io add-on."""

    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: HassioDataUpdateCoordinator,
        addon: dict[str, Any],
        attribute_name: str,
        sensor_name: str,
    ) -> None:
        """Initialize base entity."""
        self.addon_slug = addon[ATTR_SLUG]
        self.attribute_name = attribute_name
        self._attr_name = f"{addon[ATTR_NAME]}: {sensor_name}"
        self._attr_unique_id = f"{addon[ATTR_SLUG]}_{attribute_name}"
        self._attr_device_info = {"identifiers": {(DOMAIN, addon[ATTR_SLUG])}}
        super().__init__(coordinator)

    @property
    def addon_info(self) -> dict[str, Any]:
        """Return add-on info."""
        return self.coordinator.data["addons"][self.addon_slug]


class HassioOSEntity(CoordinatorEntity):
    """Base Entity for Hass.io OS."""

    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: HassioDataUpdateCoordinator,
        attribute_name: str,
        sensor_name: str,
    ) -> None:
        """Initialize base entity."""
        self.attribute_name = attribute_name
        self._attr_name = f"Home Assistant Operating System: {sensor_name}"
        self._attr_unique_id = f"home_assistant_os_{attribute_name}"
        self._attr_device_info = {"identifiers": {(DOMAIN, "OS")}}
        super().__init__(coordinator)

    @property
    def os_info(self) -> dict[str, Any]:
        """Return OS info."""
        return self.coordinator.data["os"]
