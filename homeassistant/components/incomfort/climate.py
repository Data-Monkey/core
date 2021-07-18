"""Support for an Intergas boiler via an InComfort/InTouch Lan2RF gateway."""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN, ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_HEAT,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS

from . import DOMAIN, IncomfortEntity


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up an InComfort/InTouch climate device."""
    if discovery_info is None:
        return

    client = hass.data[DOMAIN]["client"]
    heaters = hass.data[DOMAIN]["heaters"]

    async_add_entities(
        [InComfortClimate(client, h, r) for h in heaters for r in h.rooms]
    )


class InComfortClimate(IncomfortEntity, ClimateEntity):
    """Representation of an InComfort/InTouch climate device."""

    _attr_hvac_mode = HVAC_MODE_HEAT
    _attr_hvac_modes = [HVAC_MODE_HEAT]
    _attr_max_temp = 30.0
    _attr_min_temp = 5.0
    _attr_supported_features = SUPPORT_TARGET_TEMPERATURE
    _attr_temperature_unit = TEMP_CELSIUS

    def __init__(self, client, heater, room) -> None:
        """Initialize the climate device."""
        super().__init__()

        self._attr_unique_id = f"{heater.serial_no}_{room.room_no}"
        self.entity_id = f"{CLIMATE_DOMAIN}.{DOMAIN}_{room.room_no}"
        self._attr_name = f"Thermostat {room.room_no}"

        self._client = client
        self._room = room

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the device state attributes."""
        return {"status": self._room.status}

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._room.room_temp

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return self._room.setpoint

    async def async_set_temperature(self, **kwargs) -> None:
        """Set a new target temperature for this zone."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        await self._room.set_override(temperature)

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new target hvac mode."""
