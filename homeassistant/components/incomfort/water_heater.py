"""Support for an Intergas boiler via an InComfort/Intouch Lan2RF gateway."""
from __future__ import annotations

import asyncio
import logging

from aiohttp import ClientResponseError

from homeassistant.components.water_heater import (
    DOMAIN as WATER_HEATER_DOMAIN,
    WaterHeaterEntity,
)
from homeassistant.const import TEMP_CELSIUS
from homeassistant.helpers.dispatcher import async_dispatcher_send

from . import DOMAIN, IncomfortEntity

_LOGGER = logging.getLogger(__name__)

HEATER_ATTRS = ["display_code", "display_text", "is_burning"]


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up an InComfort/Intouch water_heater device."""
    if discovery_info is None:
        return

    client = hass.data[DOMAIN]["client"]
    heaters = hass.data[DOMAIN]["heaters"]

    async_add_entities([IncomfortWaterHeater(client, h) for h in heaters])


class IncomfortWaterHeater(IncomfortEntity, WaterHeaterEntity):
    """Representation of an InComfort/Intouch water_heater device."""

    _attr_icon = "mdi:thermometer-lines"
    _attr_max_temp = 80.0
    _attr_min_temp = 30.0
    _attr_name = "Boiler"
    _attr_supported_features = TEMP_CELSIUS

    def __init__(self, client, heater) -> None:
        """Initialize the water_heater device."""
        super().__init__()

        self._attr_unique_id = f"{heater.serial_no}"
        self.entity_id = f"{WATER_HEATER_DOMAIN}.{DOMAIN}"

        self._client = client
        self._heater = heater

    async def async_update(self) -> None:
        """Get the latest state data from the gateway."""
        try:
            await self._heater.update()

        except (ClientResponseError, asyncio.TimeoutError) as err:
            _LOGGER.warning("Update failed, message is: %s", err)

        else:
            async_dispatcher_send(self.hass, DOMAIN)

        self._attr_extra_state_attributes = {
            k: v for k, v in self._heater.status.items() if k in HEATER_ATTRS
        }
        if self._heater.is_tapping:
            self._attr_current_temperature = self._heater.tap_temp
        elif self._heater.is_pumping:
            self._attr_current_temperature = self._heater.heater_temp
        else:
            self._attr_current_temperature = max(
                self._heater.heater_temp, self._heater.tap_temp
            )
        if self._heater.is_failed:
            self._attr_current_operation = f"Fault code: {self._heater.fault_code}"
        else:
            self._attr_current_operation = self._heater.display_text
